#!/usr/bin/env bash
# Quick development setup
set -e

echo "🚀 Setting up AI Startup Bot..."

# Create venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install deps
echo "Installing dependencies..."
pip install -U pip
pip install -r requirements.txt

# Copy .env if missing
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Edit .env with your tokens before running!"
fi

# Create dirs
mkdir -p logs generated data backups

# Init DB
echo "Initializing database (needs DATABASE_URL set)..."
python -c "from db.models import init_db; import asyncio; asyncio.run(init_db())" || echo "⚠️  DB init skipped (DB not running?)"

echo "✅ Setup complete. Run: source .venv/bin/activate && python main.py"
