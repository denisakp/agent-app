"""Chat endpoint: the only route that depends on the gateway."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import ChatRequest, ChatResponse
from app.services.llm import LLMGateway, LLMGatewayError, get_gateway
from app.state import RequestCounter, get_counter, served_by

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    gateway: LLMGateway = Depends(get_gateway),
    counter: RequestCounter = Depends(get_counter),
) -> ChatResponse:
    """Forward the message to the gateway and return the model's reply.

    Raises:
        HTTPException: 502 when the gateway call fails.
    """
    try:
        reply = await gateway.complete(request.message)
    except LLMGatewayError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"upstream error: {exc}",
        ) from None

    await counter.increment()
    return ChatResponse(reply=reply, served_by=served_by())
