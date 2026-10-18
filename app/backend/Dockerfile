FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY papertrail ./papertrail
COPY scripts ./scripts
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.12-slim

WORKDIR /app
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
COPY --from=build --chown=10001:10001 /app /app
USER 10001
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX=/tmp
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
CMD ["uvicorn", "papertrail.main:app", "--host", "0.0.0.0", "--port", "8000"]
