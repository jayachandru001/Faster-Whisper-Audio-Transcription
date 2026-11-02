"""FastAPI Web Application Entrypoint."""

import os
# Prevent Intel MKL memory allocation errors and thread thrashing on Windows
os.environ.setdefault("CT2_USE_MKL", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import logging
import json
import uuid
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

# Configure structured logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("whisper_app")

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from whisper_service import is_cuda_available, ensure_model_downloaded, get_whisper_model
import ctranslate2

from config import MODEL_NAME
from database import (
    init_db,
    db_create_job,
    db_get_job,
    db_delete_job,
    db_list_recent_jobs,
)
from events import set_event_loop, subscribe_job, unsubscribe_job
from storage import (
    validate_audio_extension,
    save_upload_file,
    cleanup_file,
)
from subtitles import to_srt, to_vtt
from pipeline import run_transcription_pipeline
from ui import get_frontend_html


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & teardown lifecycle."""
    init_db()
    set_event_loop(asyncio.get_running_loop())

    # Automatically download and warm up Faster-Whisper model on hosting service startup
    logger.info("[Startup] Checking Faster-Whisper model...")
    try:
        model_path = await asyncio.to_thread(ensure_model_downloaded)
        logger.info("[Startup] Model verified at '%s'. Pre-warming engine...", model_path)
        await asyncio.to_thread(get_whisper_model, "cpu")
        logger.info("[Startup] Faster-Whisper engine ready for incoming requests.")
    except Exception as exc:
        logger.warning("[Startup] Model startup check: %s", exc)

    yield


app = FastAPI(
    title="Whisper Audio Transcription Service",
    version="2.0.0-modular",
    description="High-performance, zero-infrastructure Whisper transcription microservice.",
    lifespan=lifespan,
)

# Automatic response compression (>1000 bytes)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index_page():
    """Serve the interactive audio upload and transcription frontend."""
    return HTMLResponse(content=get_frontend_html())


@app.get("/health", tags=["Health"])
def health_endpoint():
    """Liveness and hardware detection probe."""
    cuda_ok = is_cuda_available()
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "gpu_available": cuda_ok,
        "cuda_device_count": ctranslate2.get_cuda_device_count() if cuda_ok else 0,
    }


@app.post(
    "/api/v1/transcriptions",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Transcription"],
)
async def submit_audio_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    device: str = Form("cpu"),
    auto_delete: bool = Form(True),
):
    """Upload an audio file and dispatch asynchronous background transcription (CPU or GPU)."""
    target_device = "cuda" if device.lower() in ("gpu", "cuda") else "cpu"
    filename = file.filename or "recording.wav"
    validate_audio_extension(filename)

    job_id = str(uuid.uuid4())
    saved_path = await save_upload_file(file, job_id, filename)

    # Persist job record in SQLite with hardware preference
    db_create_job(job_id, filename, saved_path, device=target_device)

    # Queue background task (FastAPI native thread pool)
    background_tasks.add_task(
        run_transcription_pipeline,
        job_id,
        saved_path,
        language,
        target_device,
        auto_delete,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "device": target_device,
        "filename": filename,
        "message": f"Audio accepted and queued for processing on {target_device.upper()}.",
    }


@app.get("/api/v1/transcriptions", tags=["Transcription"])
def list_recent_transcriptions(limit: int = Query(10, ge=1, le=50)):
    """Retrieve list of recent transcription jobs."""
    return db_list_recent_jobs(limit=limit)


@app.get("/api/v1/transcriptions/{job_id}", tags=["Transcription"])
def get_job_status(job_id: str):
    """Poll job status and real-time progress percentage."""
    row = db_get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    progress_val = row["progress"] if "progress" in row.keys() else 0
    device_val = (row["device"] if "device" in row.keys() else "cpu") or "cpu"
    return {
        "job_id": row["id"],
        "status": row["status"],
        "progress": progress_val or 0,
        "device": device_val,
        "filename": row["filename"],
        "language": row["language"],
        "duration": row["duration"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
        "error": row["error"],
    }


@app.get("/api/v1/transcriptions/{job_id}/events", tags=["Transcription"])
async def stream_job_events(job_id: str):
    """Server-Sent Events (SSE) push stream for live progress updates (ideal for long audio)."""
    row = db_get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # 1. Immediately yield initial state from database
        initial_state = {
            "job_id": row["id"],
            "status": row["status"],
            "progress": (row["progress"] if "progress" in row.keys() else 0) or 0,
            "language": row["language"],
            "duration": row["duration"],
            "error": row["error"],
        }
        yield f"data: {json.dumps(initial_state)}\n\n"

        if row["status"] in ("completed", "failed"):
            return

        # 2. Subscribe to in-memory event hub (0% CPU / zero DB polling)
        q = subscribe_job(job_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ("completed", "failed"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive comment to prevent reverse proxies / cloud timeouts
                    yield ": keepalive\n\n"
        finally:
            unsubscribe_job(job_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/transcriptions/{job_id}/result", tags=["Transcription"])
def get_job_result(job_id: str):
    """Retrieve full transcript and segment timestamps for a completed job."""
    row = db_get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] == "failed":
        raise HTTPException(status_code=400, detail=f"Job failed: {row['error']}")
    if row["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Job is currently '{row['status']}'")

    segments = json.loads(row["segments_json"]) if row["segments_json"] else []
    device_val = (row["device"] if "device" in row.keys() else "cpu") or "cpu"
    return {
        "job_id": row["id"],
        "status": row["status"],
        "device": device_val,
        "language": row["language"],
        "duration": row["duration"],
        "text": row["text"],
        "segments": segments,
    }


@app.get("/api/v1/transcriptions/{job_id}/download", tags=["Export"])
def download_subtitles(
    job_id: str,
    format: str = Query("json", pattern="^(json|srt|vtt)$"),
):
    """Download transcript formatted as JSON, SRT, or WebVTT subtitle track."""
    row = db_get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Job is currently '{row['status']}'")

    segments = json.loads(row["segments_json"]) if row["segments_json"] else []

    if format == "srt":
        return Response(
            content=to_srt(segments),
            media_type="application/x-subrip",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.srt"'},
        )
    elif format == "vtt":
        return Response(
            content=to_vtt(segments),
            media_type="text/vtt",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.vtt"'},
        )
    else:
        return JSONResponse(
            content={
                "job_id": row["id"],
                "language": row["language"],
                "duration": row["duration"],
                "text": row["text"],
                "segments": segments,
            },
            headers={"Content-Disposition": f'attachment; filename="{job_id}.json"'},
        )


@app.delete("/api/v1/transcriptions/{job_id}", tags=["Transcription"])
def delete_transcription_job(job_id: str):
    """Delete a transcription job from the database and remove the audio file."""
    file_path = db_delete_job(job_id)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Job not found")

    cleanup_file(file_path)
    return {"job_id": job_id, "message": "Job and audio file successfully deleted."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
