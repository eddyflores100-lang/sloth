#!/usr/bin/env bash
# nightly entry: make sure the brain is awake, then run the night shift
set -e
cd "$(dirname "$0")/.."
RT="${SLOTH_RUNTIME:-../sloth-runtime}"
if ! curl -sf http://127.0.0.1:8750/health >/dev/null; then
  "$RT/llama-b11756/llama-server" -m "$RT/gemma-3-1b-it-Q4_K_M.gguf" \
    -c 4096 --host 127.0.0.1 --port 8750 --threads 2 -ngl 0 &
  sleep 8
fi
exec python3 bin/sloth night --dir "${SLOTH_TARGET_DIR:-$HOME/Downloads}" ${SLOTH_LABELS:+--labels}
