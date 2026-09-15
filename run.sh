#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python main.py
else
  echo "Error: virtual environment not found."
  echo "Create it with: python3 -m venv .venv"
  echo "Then install dependencies: .venv/bin/pip install -r requirements.txt"
  exit 1
fi
