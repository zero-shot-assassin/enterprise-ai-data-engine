FROM python:3.12-slim-bookworm AS base

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# deps layer — only rebuilt when lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/api/app ./app
EXPOSE 8000
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Worker target: same codebase, adds the `worker` extra (docling + CPU torch).
FROM base AS worker
RUN uv sync --frozen --no-dev --no-install-project --extra worker
CMD ["uv", "run", "--frozen", "--no-dev", "celery", "-A", "app.worker.tasks", "worker", "--loglevel=info", "--concurrency=2"]
