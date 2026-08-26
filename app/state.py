"""In-memory request counter.

Deliberately *not* shared and *not* persisted: the counter lives in the process
and resets when it restarts. Running several replicas therefore produces several
independent counters, which is exactly what the workshop demonstrates.
"""

import asyncio
import socket

from fastapi import Request


class RequestCounter:
    """Counts successfully served chat requests for this process only."""

    def __init__(self) -> None:
        self._total = 0
        self._lock = asyncio.Lock()

    async def increment(self) -> int:
        """Add one to the counter and return the new value."""
        async with self._lock:
            self._total += 1
            return self._total

    @property
    def total(self) -> int:
        """Return the number of requests served by this process."""
        return self._total


def served_by() -> str:
    """Return the container hostname, which is the pod name on Kubernetes."""
    return socket.gethostname()


def get_counter(request: Request) -> RequestCounter:
    """Provide the counter created at startup (FastAPI dependency)."""
    return request.app.state.counter
