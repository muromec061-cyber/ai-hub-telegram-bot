#!/usr/bin/env bash
# OpenClaw sidecar installer
# Clones the official OpenClaw repo and prepares it for runtime.

set -e
OPENCLAW_DIR="${1:-./openclaw}"

if [ -d "$OPENCLAW_DIR/.git" ]; then
    echo "[openclaw] already installed at $OPENCLAW_DIR"
    cd "$OPENCLAW_DIR"
    git pull --ff-only || true
    cd -
else
    echo "[openclaw] cloning https://github.com/openclaw/openclaw into $OPENCLAW_DIR"
    git clone --depth 1 https://github.com/openclaw/openclaw.git "$OPENCLAW_DIR"
fi

cd "$OPENCLAW_DIR"

# Node.js deps
if [ -f package.json ]; then
    if command -v npm >/dev/null 2>&1; then
        echo "[openclaw] installing npm deps"
        npm install --omit=dev --no-audit --no-fund || true
    else
        echo "[openclaw] WARNING: npm not available; cannot install deps"
    fi
fi

# Create .env if missing
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "[openclaw] .env created from .env.example — edit it before running"
fi

echo "[openclaw] ready at $OPENCLAW_DIR"
echo "  Start: cd $OPENCLAW_DIR && npm start"
echo "  Or use the bundled manager:  python -m workers.openclaw"
