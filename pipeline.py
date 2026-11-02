"""Asynchronous background transcription task pipeline with bounded worker pool."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from config import MAX_CONCURRENT_JOBS, AUTO_DELETE_AUDIO
from database import db_update_status, db_complete_job, db_update_progress
from whisper_service import transcribe_audio_file, clear_model_memory
from events import broadcast_job_event
from storage import cleanup_file

logger = logging.getLogger(__name__)

# Dedicated bounded thread pool to prevent CPU thread thrashing
inference_pool = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_JOBS,
    thread_name_prefix="whisper_worker",
)


def _transcribe_worker(
    job_id: str,
    file_path: str,
    language: Optional[str] = None,
    device: str = "cpu",
    auto_delete: bool = AUTO_DELETE_AUDIO,
) -> None:
    """Actual CPU or GPU inference work executed within the bounded pool."""
    try:
        db_update_status(job_id, "processing")
        broadcast_job_event(job_id, {
            "job_id": job_id,
            "status": "processing",
            "progress": 0,
            "device": device,
            "duration": None,
            "error": None,
        })

        last_emitted_pct = -1

        def on_progress(pct: int, cur_sec: float, total_sec: float):
            nonlocal last_emitted_pct
            if pct != last_emitted_pct:
                last_emitted_pct = pct
                db_update_progress(job_id, pct)
                broadcast_job_event(job_id, {
                    "job_id": job_id,
                    "status": "processing",
                    "progress": pct,
                    "device": device,
                    "duration": total_sec,
                    "error": None,
                })

        logger.info("[Pipeline] Job %s starting transcription on %s...", job_id, device.upper())
        result = transcribe_audio_file(
            file_path,
            language=language,
            device=device,
            progress_callback=on_progress,
        )
        db_complete_job(
            job_id=job_id,
            language=result["language"],
            duration=result["duration"],
            text=result["text"],
            segments=result["segments"],
        )

        # Auto-delete audio file from disk after successful transcription
        if auto_delete:
            cleanup_file(file_path)

        logger.info("[Pipeline] Job %s completed successfully in %.2fs.", job_id, result["duration"])
        broadcast_job_event(job_id, {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "device": result.get("device", device),
            "language": result["language"],
            "duration": result["duration"],
            "error": None,
        })
    except Exception as exc:
        err_msg = str(exc)
        if "mkl_malloc" in err_msg.lower() or "memory" in err_msg.lower():
            logger.warning("[Pipeline] Memory pressure detected on job %s (%s). Purging model memory...", job_id, err_msg)
            clear_model_memory()
        logger.exception("[Pipeline] Job %s failed: %s", job_id, err_msg)
        if auto_delete:
            cleanup_file(file_path)
        db_update_status(job_id, "failed", error=err_msg)
        broadcast_job_event(job_id, {
            "job_id": job_id,
            "status": "failed",
            "progress": 0,
            "device": device,
            "duration": None,
            "error": err_msg,
        })


def run_transcription_pipeline(
    job_id: str,
    file_path: str,
    language: Optional[str] = None,
    device: str = "cpu",
    auto_delete: bool = AUTO_DELETE_AUDIO,
) -> None:
    """Submit job to the bounded worker pool queue."""
    inference_pool.submit(_transcribe_worker, job_id, file_path, language, device, auto_delete)
