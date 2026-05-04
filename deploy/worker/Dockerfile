# syntax=docker/dockerfile:1

### Stage 1: builder
FROM python:3.13-slim AS builder
WORKDIR /build

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --format requirements-txt -o requirements.txt

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
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY src/backend ./src/backend
COPY src/shared  ./src/shared

RUN chown -R appuser:appuser /app
USER appuser

# No CMD — each worker container specifies its own command in docker-compose
