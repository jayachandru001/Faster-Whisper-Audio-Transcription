# 🎙️ Whisper Audio Transcription Microservice

A high-performance audio transcription microservice and interactive studio powered by **FastAPI** and **Faster-Whisper (CTranslate2)**.

Features zero external dependencies (no Redis, no Celery), built-in CPU/GPU acceleration, real-time Server-Sent Events (SSE) tracking, acoustic silence chunking, and instant subtitle exports.

---

## 📑 Table of Contents
- [Architecture & Execution Flow](#-architecture--execution-flow)
- [Codebase Structure](#-codebase-structure)
- [Acoustic Chunking Strategy](#-acoustic-chunking-strategy)
- [Model & Quantization](#-model--quantization)
- [Quick Start](#-quick-start)
- [Interactive Web UI](#-interactive-web-ui)
- [REST API Reference](#-rest-api-reference)
- [Configuration](#-configuration)
- [Memory Management & Fault Recovery](#-memory-management--fault-recovery)

---

## 🔄 Architecture & Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client (UI / API)
    participant Main as FastAPI (main.py)
    participant Storage as Disk (storage.py)
    participant DB as SQLite WAL (database.py)
    participant Worker as ThreadPool (pipeline.py)
    participant Whisper as Engine (whisper_service.py)
    participant SSE as Events (events.py)

    Client->>Main: POST /api/v1/transcriptions (audio file, device, language)
    Main->>Storage: Stream in 1 MB chunks to disk (limit <= 500 MB)
    Main->>DB: Create job (status: queued)
    Main->>Worker: Dispatch background task
    Main-->>Client: HTTP 202 Accepted {"job_id": "...", "status": "queued"}

    Client->>SSE: GET /api/v1/transcriptions/{job_id}/events (connect SSE)
    Worker->>DB: Update status -> processing
    Worker->>SSE: Broadcast progress: 0%

    Worker->>Whisper: transcribe_audio_file()
    Whisper->>Whisper: Probe duration via PyAV (<10ms)
    alt Duration < 300s (Route A: Single Pass)
        Whisper->>Whisper: model.transcribe() (full context, zero chunk overhead)
    else Duration >= 300s (Route B: Parallel VAD Batched)
        Whisper->>Whisper: batched_pipeline.transcribe() (Silero VAD, batch_size=2|8)
    end
    Whisper-->>Worker: Stream segment progress -> DB & SSE

    Worker->>DB: Save transcript, segments, words (status: completed)
    Worker->>SSE: Broadcast completed (100%)
    opt auto_delete is true
        Worker->>Storage: Delete audio from disk
    end
    SSE-->>Client: Push completion event (100%)
    Client->>Main: GET /api/v1/transcriptions/{job_id}/result
    Main->>DB: Fetch completed transcript & segments
    DB-->>Main: Return transcript & timestamps
    Main-->>Client: HTTP 200 OK (Full text, segment timestamps & subtitle exports)
```

### Pipeline Summary
1. **$O(1)$ Memory Upload:** Streamed in 1 MB chunks directly to disk; rejects files over 500 MB with `HTTP 413`.
2. **Instant Handshake:** Validates format, records job in SQLite WAL, and returns `HTTP 202` in $<100\text{ms}$.
3. **Isolated Thread Pool:** Background jobs run on `ThreadPoolExecutor(max_workers=1)` to prevent CPU event-loop starvation.
4. **PyAV Pre-flight Probe:** Inspects container metadata in $<10\text{ms}$ to route by length (<5 min vs $\ge$5 min).
5. **Real-Time Push & Export:** Progress broadcasts over SSE; outputs formatted `.srt`, `.vtt`, and `.json`.

---

## 📁 Codebase Structure

```text
Audio_Voice_Transcription/
├── main.py              # FastAPI app, lifespan setup & REST endpoints
├── config.py            # Environment variables, constants & defaults
├── whisper_service.py   # Model caching, PyAV probe, VAD inference & memory retry
├── pipeline.py          # Bounded ThreadPool worker & async pipeline runner
├── database.py          # SQLite WAL connection & atomic job CRUD
├── events.py            # SSE pub/sub broker with 15s keepalive ping
├── storage.py           # 1 MB chunked streaming upload & cleanup
├── subtitles.py         # SubRip (.srt) and WebVTT (.vtt) formatters
├── ui.py                # Single-page studio UI (Tailwind CSS, recorder, player)
├── requirements.txt     # Python dependencies
└── storage/             # Model weights, database & temporary uploads
```

| Module | Role | Key Functions / Responsibilities |
| :--- | :--- | :--- |
| `main.py` | API Gateway | Endpoints for upload, status, SSE stream, result, and subtitle download |
| `config.py` | Settings | Paths, `CHUNK_MIN_DURATION_SEC` (300s), `MAX_UPLOAD_SIZE_BYTES` (500 MB) |
| `whisper_service.py` | Inference Engine | `probe_audio_duration`, `get_whisper_model`, `transcribe_audio_file`, `clear_model_memory` |
| `pipeline.py` | Task Queue | `inference_pool` (`max_workers=1`), `_transcribe_worker` |
| `database.py` | Persistence | SQLite WAL mode, `db_create_job`, `db_update_progress`, `db_complete_job` |
| `events.py` | Live SSE Broker | `subscribe_job`, `broadcast_job_event`, `job_event_generator` (15s heartbeat) |
| `storage.py` | File I/O | `save_upload_file` (1 MB streaming chunks, 500 MB limit), `cleanup_file` |
| `subtitles.py` | Subtitle Export | `to_srt` (HH:MM:SS,mmm), `to_vtt` (HH:MM:SS.mmm) |
| `ui.py` | Studio UI | Audio drag-and-drop, in-browser player, microphone recorder, live SSE bar |

---

## ⚡ Acoustic Chunking Strategy

### Why Clock Slicing Fails vs Silero VAD
- **Fixed Clock Slicing (e.g. every 30s):** Cuts words in half mid-phoneme (e.g., `trans-` / `-cription`). This forces Whisper's autoregressive decoder into hallucination loops and broken timestamps.
- **Silero VAD Silence Chunking:** Slices audio strictly at natural breath and speech pauses ($>500\text{ms}$ silence gaps). Words and phonemes remain 100% intact.

### 5-Minute Dual-Route Logic
| Route | Condition | Engine Path | Rationale |
| :--- | :--- | :--- | :--- |
| **Route A** | `< 5 min` ($< 300\text{s}$) | `model.transcribe()` | Single continuous pass. Preserves full cross-attention context; zero chunking overhead for short memos. |
| **Route B** | `≥ 5 min` ($\ge 300\text{s}$) | `batched_pipeline.transcribe()` | Slices at VAD pauses and infers in parallel batches (`batch_size=2` CPU, `8` GPU). 3x–6x speedup on long audio. |

### Custom VAD Edge-Protection Parameters
```python
vad_parameters = dict(
    min_speech_duration_ms=100,  # Lowered from 250ms to catch short words ("Hi", "Yes", "No")
    speech_pad_ms=300,           # 300ms buffer before/after speech to protect plosive consonants
    threshold=0.4                # Lowered from 0.5 to detect soft/low-gain voices
)
```

- **Global Timestamp Reassembly:** Segment timestamps are offset by chunk starts ($t_{\text{global}} = \text{chunk\_start} + t_{\text{local}}$), preserving monotonic subtitle order.
- **Progress Tracking:** Calculated as $\min(99, \operatorname{round}(t_{\text{current}} / t_{\text{total}} \times 100))$, hitting 100% upon database commit.

---

## 🧠 Model & Quantization

- **CPU (Default):** Quantized to **INT8** (`compute_type="int8"`). Uses 70% less RAM (<600 MB) and runs 4x faster than FP32.
- **GPU (CUDA):** Half-precision **FP16** (`compute_type="float16"`). Auto-detected on startup; falls back to CPU if unavailable.
- **Default Local Weights:** Loaded from `storage/model/` (Faster-Whisper `base` model, ~145 MB).
- **Model Source / Download:** Downloaded from Hugging Face repository: [Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base) (`https://huggingface.co/Systran/faster-whisper-base`).

---

## 📦 Quick Start

```bash
# 1. Setup virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1       # On Linux/macOS: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start service
python main.py
```

- **Web Studio UI:** `http://localhost:8000`
- **Swagger API Docs:** `http://localhost:8000/docs`

---

## 🎨 Interactive Web UI

Open `http://localhost:8000` for the built-in studio:
- **Audio Preview:** In-browser player (`<audio controls>`) with file info.
- **Microphone Recorder:** Record 16 kHz audio directly in the browser.
- **Hardware Selector:** Toggle between CPU (int8) and GPU (float16).
- **Live Progress:** Real-time progress bar powered by SSE (`12:30 / 60:00 · 21%`).
- **Instant Export:** One-click downloads for **SRT**, **VTT**, and **JSON**.

---

## 🔌 REST API Reference

### 1. Submit Audio
`POST /api/v1/transcriptions` (Returns `202 Accepted`)
```bash
curl -X POST "http://localhost:8000/api/v1/transcriptions" \
  -F "file=@sample.mp3" \
  -F "device=cpu" \
  -F "language=en"
```

### 2. Stream Live Progress (SSE)
`GET /api/v1/transcriptions/{job_id}/events`
```bash
curl -N "http://localhost:8000/api/v1/transcriptions/{job_id}/events"
```

### 3. Get Result
`GET /api/v1/transcriptions/{job_id}/result`

### 4. Download Subtitles
`GET /api/v1/transcriptions/{job_id}/download?format=srt` (`srt`, `vtt`, or `json`)

---

## ⚙️ Configuration

Set via environment variables or edit `config.py`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `STORAGE_DIR` | `./storage` | Directory for DB, uploads, and model cache |
| `WHISPER_MODEL` | `storage/model` | Path to local model folder or HuggingFace ID |
| `WHISPER_CPU_THREADS` | `2` | Worker threads per CTranslate2 instance |
| `CHUNK_MIN_DURATION_SEC` | `300.0` | Minimum seconds to trigger parallel VAD batching (5 min) |
| `MAX_UPLOAD_SIZE_BYTES` | `524288000` | Upload limit in bytes (500 MB) |
| `MAX_CONCURRENT_JOBS` | `1` | Max concurrent inference jobs |
| `AUTO_DELETE_AUDIO` | `true` | Delete audio file after transcription |

---

## 🛡️ Memory Management & Fault Recovery

1. **Windows Intel MKL Shield:** Sets `CT2_USE_MKL="0"` and `MKL_NUM_THREADS="1"` at startup to prevent `mkl_malloc: failed to allocate memory` errors under memory pressure.
2. **Auto-Recovery Retry:** On memory errors, the engine calls `clear_model_memory()` (`gc.collect()`, cache flush) and retries transcription with a minimal thread footprint.
3. **SSE Keepalive:** Emits `: keepalive\n\n` comments every 15 seconds to prevent browser and reverse proxy timeouts.
