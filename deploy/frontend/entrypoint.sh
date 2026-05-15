#!/bin/bash
set -e

exec uvicorn src.frontend.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
