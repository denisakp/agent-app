"""Client for the LiteLLM gateway.

The gateway speaks the OpenAI-compatible chat completions API. We call it with a
plain HTTP POST rather than an SDK so that the request shape stays visible.
"""

from typing import Any

import httpx
from fastapi import Request

from app.config import Settings


class LLMGatewayError(RuntimeError):
    """Raised when the gateway cannot be reached or answers unusably."""


class LLMGateway:
    """Sends chat completions to the gateway over a shared HTTP client."""

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def complete(self, message: str) -> str:
        """Send one user message to the gateway and return the model's reply.

        Raises:
            LLMGatewayError: on network failure, non-2xx status, or a payload
                that does not carry a reply. The API key never appears in the
                error message.
        """
        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": [{"role": "user", "content": message}],
        }
        headers = {"Authorization": f"Bearer {self._settings.llm_api_key}"}

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMGatewayError(
                f"gateway returned HTTP {exc.response.status_code}"
            ) from None
        except httpx.HTTPError:
            raise LLMGatewayError("gateway unreachable") from None

        try:
            return str(response.json()["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError):
            raise LLMGatewayError("gateway returned an unexpected payload") from None


def get_gateway(request: Request) -> LLMGateway:
    """Provide the gateway client created at startup (FastAPI dependency)."""
    return request.app.state.gateway
