"""Application configuration, loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the agent.

    Every value comes from the environment. The application knows nothing about
    the provider sitting behind the gateway: it only knows the gateway.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_base_url: str = Field(
        description="Base URL of the LiteLLM gateway, e.g. https://gateway.example.com/v1",
    )
    llm_api_key: str = Field(
        description="LiteLLM virtual key. Required: the app refuses to start without it.",
    )
    llm_model: str = Field(
        default="chat",
        description="Model alias exposed by the gateway.",
    )
    request_timeout: float = Field(
        default=30.0,
        description="Timeout in seconds for a single call to the gateway.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, failing fast if any are missing."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as exc:
        # Report only the variable names, never the values: LLM_API_KEY is a secret.
        names = ", ".join(str(error["loc"][0]).upper() for error in exc.errors())
        raise RuntimeError(
            f"Invalid or missing environment variables: {names}. "
            "Set them before starting the application."
        ) from None
