#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt

# Check ffmpeg/ffprobe
if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found on PATH. Install with: brew install ffmpeg"
    exit 1
fi
if ! command -v ffprobe &>/dev/null; then
    echo "ERROR: ffprobe not found on PATH. Install with: brew install ffmpeg"
    exit 1
fi

echo "ffmpeg and ffprobe found."

# Remind about API key
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo ""
    echo "REMINDER: Set your Gemini API key before running:"
    echo "  export GEMINI_API_KEY=your-key-here"
    echo "  (or add it to a .env file in this directory)"
fi

echo ""
echo "Setup complete. Activate with: source .venv/bin/activate"
