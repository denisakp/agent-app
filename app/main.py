"""Application factory: builds the app, wires shared objects, mounts routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.routers import chat, health, stats
from app.services.llm import LLMGateway
from app.state import RequestCounter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the shared HTTP client and counter, and close the client on exit."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        app.state.gateway = LLMGateway(client, settings)
        app.state.counter = RequestCounter()
        yield


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    application = FastAPI(
        title="Agent App",
        description="A minimal AI agent that forwards messages to an LLM gateway.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(chat.router)
    application.include_router(stats.router)
    application.include_router(health.router)
    return application


app = create_app()
