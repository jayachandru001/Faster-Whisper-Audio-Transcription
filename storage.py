"""Audio file validation and storage management."""

import os
from fastapi import UploadFile, HTTPException
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES


def validate_audio_extension(filename: str) -> str:
    """Validate that the uploaded file has a supported audio extension."""
    if "." not in filename:
        raise HTTPException(status_code=400, detail="Filename missing extension.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed extensions: {allowed}",
        )
    return ext


CHUNK_SIZE = 1024 * 1024  # 1MB buffer


async def save_upload_file(file: UploadFile, job_id: str, filename: str) -> str:
    """Save uploaded audio to disk in 1MB chunks to ensure constant O(1) memory usage (up to 500MB)."""
    safe_name = f"{job_id}_{filename}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)
    total_bytes = 0
    with open(save_path, "wb") as f:
        while chunk := await file.read(CHUNK_SIZE):
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                f.close()
                cleanup_file(save_path)
                max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowed upload size of {max_mb} MB.",
                )
            f.write(chunk)
    return save_path


def cleanup_file(file_path: str | None) -> None:
    """Safely remove a file from disk if it exists."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
