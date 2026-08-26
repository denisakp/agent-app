"""Request and response models exposed by the HTTP API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A single user message sent to the agent."""

    message: str = Field(min_length=1, description="Text sent to the model.")


class ChatResponse(BaseModel):
    """The model's answer, plus the instance that produced it."""

    reply: str
    served_by: str


class StatsResponse(BaseModel):
    """Counters held by the instance that answered."""

    total_requests: int
    served_by: str


class HealthResponse(BaseModel):
    """Liveness answer consumed by the Kubernetes probes."""

    status: str
