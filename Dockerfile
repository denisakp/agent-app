FROM python:3.11-slim

LABEL org.opencontainers.image.title="ai-agent-workshop" \
      org.opencontainers.image.description="Agent IA minimal pour le workshop Kubernetes & Agents IA" \
      org.opencontainers.image.authors="Denis AKPAGNONITE <hello@denisakp.me>" \
      org.opencontainers.image.source="https://github.com/denisakp/agent-app" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Never run as root.
RUN useradd --create-home --uid 1000 agent
USER agent

EXPOSE 8000

# No configuration is baked in: LLM_BASE_URL, LLM_API_KEY and LLM_MODEL are
# passed at runtime.
CMD ["fastapi", "run", "main.py", "--port", "8000"]
