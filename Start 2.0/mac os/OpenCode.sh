#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NODE_HOME="$ROOT/AI/node"
OPENCODE_HOME="$ROOT/AI/OpenCode"
OPENCODE_BIN="$OPENCODE_HOME/opencode"
CONFIG="$ROOT/AI/config/opencode.json"
[[ -x "$OPENCODE_BIN" ]] || { echo "[ERROR] OpenCode not found or not executable: $OPENCODE_BIN"; exit 1; }
[[ -d "$NODE_HOME" ]] && export PATH="$NODE_HOME:$PATH"
[[ -d "$OPENCODE_HOME" ]] && export PATH="$OPENCODE_HOME:$PATH"
export OPENCODE_CONFIG="$CONFIG"
echo "Starting OpenCode (macOS)..."
exec "$OPENCODE_BIN"
