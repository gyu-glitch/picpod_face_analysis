#!/bin/bash
cd "$(dirname "$0")"
mkdir -p result
if [ -x .venv/bin/python ]; then
  .venv/bin/python receiver.py
else
  python3 receiver.py
fi
