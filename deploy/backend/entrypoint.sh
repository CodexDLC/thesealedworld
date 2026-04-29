#!/bin/bash
set -e

exec uvicorn src.backend.app:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level info
