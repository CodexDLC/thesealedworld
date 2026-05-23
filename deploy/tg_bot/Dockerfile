# syntax=docker/dockerfile:1

### Stage 1: builder
FROM python:3.13-slim AS builder
WORKDIR /build

RUN pip install --no-cache-dir uv==0.11.8

COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --group tg-bot --no-emit-project --format requirements-txt -o requirements.txt

RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

### Stage 2: runtime
FROM python:3.13-slim AS runtime
WORKDIR /app

RUN adduser --disabled-password --uid 1000 appuser

COPY --from=builder /venv /venv

ENV PATH="/venv/bin:$PATH" \
    PYTHONPATH="/app:/app/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY src/tg_bot ./src/tg_bot
COPY src/shared ./src/shared

RUN chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "tg_bot.launcher"]
