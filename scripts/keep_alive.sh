#!/usr/bin/env bash
cd /workspace/ai-startup
while true; do
  echo "[$(date)] starting bot..."
  .venv/bin/python -u main.py --mode polling
  echo "[$(date)] bot died, restarting in 3s..."
  sleep 3
done
