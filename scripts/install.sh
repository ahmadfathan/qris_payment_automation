#!/bin/bash

# Exit on error
set -e

VENV_DIR=".venv"

echo "🔧 Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install it first."
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "📂 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "⬆️ Upgrading pip..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "📜 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found. Skipping installation."
fi

echo "✅ Setup complete."