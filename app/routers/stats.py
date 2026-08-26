"""Counter endpoint, answered from this instance's memory."""

from fastapi import APIRouter, Depends

from app.schemas import StatsResponse
from app.state import RequestCounter, get_counter, served_by

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def stats(counter: RequestCounter = Depends(get_counter)) -> StatsResponse:
    """Return the request count held by the instance that answers."""
    return StatsResponse(total_requests=counter.total, served_by=served_by())
