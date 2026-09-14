#!/usr/bin/env bash
# Compatibility launcher for macOS/Linux; use audit.py directly on Windows.
set -eu
exec python3 "$(cd -- "$(dirname -- "$0")" && pwd)/audit.py" "$@"
