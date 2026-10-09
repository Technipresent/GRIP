#!/bin/sh
# Starts GRIP. When BWS_ACCESS_TOKEN is set, secrets (EXA_API_KEY, BRAVE_API_KEY) are injected
# at runtime from Bitwarden Secrets Manager; nothing secret is stored in Railway or the image.
set -e
CMD="uvicorn grip.app:build_app --factory --host 0.0.0.0 --port ${PORT:-8080}"
if [ -n "$BWS_ACCESS_TOKEN" ]; then
  exec bws run --project-id "$BWS_PROJECT_ID" -- "$CMD"
fi
exec sh -c "$CMD"
