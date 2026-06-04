# syntax=docker/dockerfile:1
#
# LOCAL-ONLY studio image.
#
# NEVER build this in CI/CD for prod. The studio app is for the developer's
# home machine, and reads prod data through an SSH tunnel on the host. This
# Dockerfile is provided as a convenience for users who prefer running studio
# in a container; the supported invocation is `uv run uvicorn ...` directly.

### Stage 1: builder
FROM python:3.13-slim AS builder
WORKDIR /build

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
# Reuses the frontend-runtime dep group — studio uses the same FastAPI / Jinja /
# Alpine stack, plus asyncpg/redis which are already in that group.
RUN uv export --frozen --no-dev --group frontend-runtime --no-emit-project --format requirements-txt -o requirements.txt

RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

### Stage 2: runtime
FROM python:3.13-slim AS runtime
WORKDIR /app

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --uid 1000 appuser

COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH" \
    PYTHONPATH="/app:/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Whitelisted COPYs — studio reuses frontend templates/static, fastapi_cabinet
# library, and shared schemas. Backend logic is imported on demand by studio
# arq workers (added in a later PR); for the infrastructure-prep PR studio
# does not require src/backend.
COPY src/studio          ./src/studio
COPY src/frontend        ./src/frontend
COPY src/fastapi_cabinet ./src/fastapi_cabinet
COPY src/shared          ./src/shared

RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["uvicorn", "src.studio.app:app", "--host", "0.0.0.0", "--port", "9100"]

HEALTHCHECK --interval=10s --timeout=5s --retries=6 \
    CMD curl -f http://localhost:9100/health || exit 1
