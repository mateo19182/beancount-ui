#!/usr/bin/env bash
# Prepare backend for Tauri bundle (run from repo root before cargo tauri build)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
DEST="$ROOT/src-tauri/resources/backend"

rm -rf "$DEST"
mkdir -p "$DEST"
cp -r "$BACKEND/app" "$BACKEND/pyproject.toml" "$BACKEND/uv.lock" "$DEST/"
cd "$DEST"
uv sync --frozen

echo "Sidecar prepared at $DEST"
