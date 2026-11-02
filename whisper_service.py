"""Faster-Whisper model loading and speech inference supporting CPU and GPU."""

import os
# Prevent Intel MKL memory allocation errors on Windows
os.environ.setdefault("CT2_USE_MKL", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import gc
import time
import logging
import ctranslate2
from typing import Optional, Dict, Any, List, Callable, Tuple
from config import MODEL_NAME, CPU_THREADS, CHUNK_MIN_DURATION_SEC, STORAGE_DIR

logger = logging.getLogger(__name__)

def ensure_model_downloaded() -> str:
    """Ensure Faster-Whisper model files exist locally; automatically download from Hugging Face if missing."""
    import faster_whisper

    local_model = os.path.join(STORAGE_DIR, "model")
    model_bin = os.path.join(local_model, "model.bin")
    if os.path.isdir(local_model) and os.path.isfile(model_bin):
        logger.info("[Whisper] Verified local model at '%s'.", local_model)
        return local_model.replace("\\", "/")

    target_repo = os.getenv("WHISPER_MODEL", "Systran/faster-whisper-base")
    logger.info(
        "[Whisper] Faster-Whisper model not found locally. Automatically downloading '%s' from Hugging Face into '%s'...",
        target_repo,
        local_model,
    )
    os.makedirs(local_model, exist_ok=True)
    downloaded_dir = faster_whisper.download_model(target_repo, output_dir=local_model)
    logger.info("[Whisper] Faster-Whisper model successfully downloaded to '%s'.", downloaded_dir)
    return downloaded_dir.replace("\\", "/")

# Custom VAD configurations to protect the beginning of chunks
DEFAULT_VAD_PARAMETERS = dict(
    min_speech_duration_ms=100,   # Lowered from 250ms so short initial words are caught
    speech_pad_ms=300,            # Adds a 300ms buffer before/after speech to prevent aggressive front clipping
    threshold=0.4,                # Slightly lowered sensitivity threshold (default is 0.5)
)

_cached_models: Dict[str, Any] = {}
_cached_batched_pipelines: Dict[str, Any] = {}


def clear_model_memory() -> None:
    """Clear all cached model and pipeline instances and force garbage collection."""
    global _cached_models, _cached_batched_pipelines
    logger.info("[Whisper] Clearing cached models and releasing memory...")
    _cached_models.clear()
    _cached_batched_pipelines.clear()
    gc.collect()


def probe_audio_duration(file_path: str) -> float:
    """Fast audio duration probe using PyAV container metadata without full decoding."""
    try:
        import av
        with av.open(file_path) as container:
            if container.duration is not None and av.time_base:
                return float(container.duration) / av.time_base
            for stream in container.streams.audio:
                if stream.duration is not None and stream.time_base is not None:
                    return float(stream.duration * stream.time_base)
    except Exception as exc:
        logger.debug("[Whisper] Duration probe note: %s", exc)
    return 0.0


def is_cuda_available() -> bool:
    """Check if NVIDIA CUDA devices are detected by CTranslate2."""
    try:
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def get_whisper_model(device: str = "cpu") -> Tuple[Any, str]:
    """Load and cache the Faster-Whisper model instance on CPU or GPU."""
    global _cached_models
    dev = device.lower().strip()
    if dev in ("gpu", "cuda"):
        if is_cuda_available():
            target_device = "cuda"
            compute_type = "float16"
        else:
            logger.warning("[Whisper] GPU requested but CUDA is not available. Falling back to CPU (int8)...")
            target_device = "cpu"
            compute_type = "int8"
    else:
        target_device = "cpu"
        compute_type = "int8"

    key = f"{target_device}_{compute_type}"
    if key not in _cached_models:
        from faster_whisper import WhisperModel
        model_path = ensure_model_downloaded()
        logger.info("[Whisper] Loading '%s' on %s (%s compute)...", model_path, target_device.upper(), compute_type)
        if target_device == "cuda":
            _cached_models[key] = WhisperModel(
                model_path,
                device="cuda",
                compute_type=compute_type,
            )
        else:
            try:
                _cached_models[key] = WhisperModel(
                    model_path,
                    device="cpu",
                    compute_type=compute_type,
                    cpu_threads=CPU_THREADS,
                )
            except RuntimeError as exc:
                if "mkl_malloc" in str(exc).lower() or "memory" in str(exc).lower():
                    logger.warning("[Whisper] Memory allocation pressure with %d threads (%s). Clearing memory and retrying with 1 thread...", CPU_THREADS, exc)
                    clear_model_memory()
                    time.sleep(0.5)
                    _cached_models[key] = WhisperModel(
                        model_path,
                        device="cpu",
                        compute_type=compute_type,
                        cpu_threads=1,
                    )
                else:
                    raise
        logger.info("[Whisper] Model on %s loaded successfully.", target_device.upper())

    return _cached_models[key], target_device


def get_batched_pipeline(device: str = "cpu") -> Tuple[Any, str]:
    """Retrieve or initialize the BatchedInferencePipeline for parallel VAD chunking."""
    global _cached_batched_pipelines
    model, used_device = get_whisper_model(device=device)
    key = f"batched_{used_device}"
    if key not in _cached_batched_pipelines:
        from faster_whisper import BatchedInferencePipeline
        _cached_batched_pipelines[key] = BatchedInferencePipeline(model=model)
        logger.info("[Whisper] BatchedInferencePipeline initialized for %s.", used_device.upper())
    return _cached_batched_pipelines[key], used_device


def transcribe_audio_file(
    file_path: str,
    language: Optional[str] = None,
    device: str = "cpu",
    progress_callback: Optional[Callable[[int, float, float], None]] = None,
    is_retry: bool = False,
) -> Dict[str, Any]:
    """Transcribe audio file, using whole-file single pass for <5 min or parallel VAD chunking for >=5 min."""
    try:
        duration_sec = probe_audio_duration(file_path)

        # If audio is less than 5 minutes (300s), process whole file directly without chunking
        if 0 < duration_sec < CHUNK_MIN_DURATION_SEC:
            logger.info(
                "[Whisper] Audio duration is %.1fs (< %.0fs). Processing whole file directly without chunking...",
                duration_sec,
                CHUNK_MIN_DURATION_SEC,
            )
            model, used_device = get_whisper_model(device=device)
            segments_iter, info = model.transcribe(
                file_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                word_timestamps=True,
                vad_parameters=DEFAULT_VAD_PARAMETERS,
            )
        else:
            logger.info(
                "[Whisper] Audio duration is %.1fs (>= %.0fs). Running parallel VAD chunked pipeline...",
                duration_sec,
                CHUNK_MIN_DURATION_SEC,
            )
            try:
                pipeline, used_device = get_batched_pipeline(device=device)
                batch_size = 8 if used_device == "cuda" else 2
                segments_iter, info = pipeline.transcribe(
                    file_path,
                    language=language,
                    batch_size=batch_size,
                    beam_size=5,
                    vad_filter=True,
                    word_timestamps=True,
                    vad_parameters=DEFAULT_VAD_PARAMETERS,
                )
            except Exception as exc:
                logger.warning("[Whisper] Batched chunking fallback to sequential stream (%s)...", exc)
                model, used_device = get_whisper_model(device=device)
                segments_iter, info = model.transcribe(
                    file_path,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                    word_timestamps=True,
                    vad_parameters=DEFAULT_VAD_PARAMETERS,
                )

        total_sec = info.duration or 0.0
        last_pct = 0
        if progress_callback and total_sec > 0:
            progress_callback(1, 0.0, total_sec)

        segments: List[Dict[str, Any]] = []
        text_parts: List[str] = []

        for s in segments_iter:
            txt = s.text.strip()
            if txt:
                text_parts.append(txt)

            words: List[Dict[str, Any]] = []
            if s.words:
                for w in s.words:
                    words.append({
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3),
                    })

            segments.append({
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": txt,
                "words": words,
            })

            if total_sec > 0 and progress_callback:
                pct = min(99, max(1, int((s.end / total_sec) * 100)))
                if pct > last_pct:
                    last_pct = pct
                    progress_callback(pct, s.end, total_sec)

        if progress_callback:
            progress_callback(100, total_sec, total_sec)

        return {
            "device": used_device,
            "language": info.language,
            "duration": info.duration,
            "text": " ".join(text_parts).strip(),
            "segments": segments,
        }
    except RuntimeError as exc:
        if not is_retry and ("mkl_malloc" in str(exc).lower() or "memory" in str(exc).lower()):
            logger.warning(
                "[Whisper] Memory error during transcription (%s). Automatically clearing model memory and retrying...",
                exc,
            )
            clear_model_memory()
            time.sleep(0.5)
            return transcribe_audio_file(
                file_path=file_path,
                language=language,
                device="cpu",
                progress_callback=progress_callback,
                is_retry=True,
            )
        raise
