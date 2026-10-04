#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="$ROOT/Colibri/c/coli"
MODEL="$ROOT/Colibri/olmoe_merged"
echo "=========================================="
echo "        POCKET AI - COLIBRI (Linux)"
echo "=========================================="
[[ -x "$CLI" ]] || { echo "[ERROR] Colibri CLI not found or not executable: $CLI"; exit 1; }
[[ -d "$MODEL" ]] || { echo "[ERROR] Colibri model directory not found: $MODEL"; exit 1; }
echo "[1] Terminal CLI"
echo "[2] Web Dashboard"
echo "[3] Exit"
read -r -p "Select: " choice
case "$choice" in
  1) exec "$CLI" chat --model "$MODEL" ;;
  2) exec "$CLI" web --model "$MODEL" ;;
  *) exit 0 ;;
esac
