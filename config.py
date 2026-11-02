"""Configuration and environment constants."""

import os

# Prevent Intel MKL / OpenMP heap exhaustion on Windows
os.environ.setdefault("CT2_USE_MKL", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
DB_PATH = os.path.join(STORAGE_DIR, "whisper.db")

# Self-contained local model path (loads from storage/model in root folder)
def _resolve_model_path() -> str:
    env_model = os.getenv("WHISPER_MODEL")
    if env_model:
        return env_model

    local_model = os.path.join(STORAGE_DIR, "model")
    if os.path.isdir(local_model) and os.path.exists(os.path.join(local_model, "model.bin")):
        return local_model.replace("\\", "/")

    return "Systran/faster-whisper-base"

MODEL_NAME = _resolve_model_path()

CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "2"))
ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "flac", "ogg", "webm", "aac", "opus"}

# Minimum audio duration (in seconds) to trigger parallel VAD chunking (default: 300s = 5 min)
CHUNK_MIN_DURATION_SEC = float(os.getenv("CHUNK_MIN_DURATION_SEC", "300.0"))

# Maximum allowed file upload size (default: 500 MB)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(500 * 1024 * 1024)))

# Maximum concurrent inference jobs
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))

# Default policy: Auto-delete audio files after transcription to preserve privacy & disk space
AUTO_DELETE_AUDIO = os.getenv("AUTO_DELETE_AUDIO", "true").lower() in ("true", "1", "yes")
