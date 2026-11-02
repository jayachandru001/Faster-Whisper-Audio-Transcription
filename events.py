"""In-memory Pub/Sub event hub for Server-Sent Events (SSE).

Decouples background worker updates from HTTP client connections,
eliminating repetitive database queries during live streaming.
"""

import asyncio
from typing import Dict, Set, Any, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_subscribers: Dict[str, Set[asyncio.Queue]] = {}


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the running asyncio event loop for thread-safe cross-thread calls."""
    global _loop
    _loop = loop


def subscribe_job(job_id: str) -> asyncio.Queue:
    """Subscribe a client queue to live job status and progress updates."""
    q: asyncio.Queue = asyncio.Queue(maxsize=32)
    _subscribers.setdefault(job_id, set()).add(q)
    return q


def unsubscribe_job(job_id: str, q: asyncio.Queue) -> None:
    """Unsubscribe client queue and clean up idle job registries."""
    if job_id in _subscribers:
        _subscribers[job_id].discard(q)
        if not _subscribers[job_id]:
            _subscribers.pop(job_id, None)


def broadcast_job_event(job_id: str, data: Dict[str, Any]) -> None:
    """Publish an update to all active SSE listener queues (thread-safe)."""
    queues = _subscribers.get(job_id)
    if not queues:
        return
    for q in list(queues):
        try:
            if _loop and _loop.is_running():
                _loop.call_soon_threadsafe(q.put_nowait, data)
            else:
                q.put_nowait(data)
        except (asyncio.QueueFull, RuntimeError):
            pass
