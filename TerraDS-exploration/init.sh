#!/bin/bash

VENV_DIR=".venv"
ZENODO_URL="https://zenodo.org/records/14217386/files/TerraDS.sqlite?download=1"
DB_FILE="TerraDS.sqlite"

# Create venv if does not exist yet
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Start venv + install
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Download TerraDS.sqlite file from Zenodo, if does not exist yet
if [ ! -f "$DB_FILE" ]; then
    curl -L "$ZENODO_URL" -o "$DB_FILE"
fi

docker build -t image_process_commit:latest .
