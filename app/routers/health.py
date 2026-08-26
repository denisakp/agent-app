"""Liveness endpoint backing the Kubernetes probes."""

from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Answer immediately, without touching any dependency."""
    return HealthResponse(status="ok")
