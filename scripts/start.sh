#!/bin/sh
set -eu
if [ "${WAIT_FOR_CHROMA:-false}" = "true" ]; then
  uv run --no-sync python -m aura.scripts.wait_for_chroma
fi
uv run --no-sync alembic upgrade head
exec uv run --no-sync uvicorn aura.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1
