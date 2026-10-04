#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GPU="$ROOT/server/llama-gpu"
CPU="$ROOT/server/llama"
Q35="$ROOT/Models/Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"
Q25="$ROOT/Models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
echo "=========================================="
echo "       POCKET AI MODEL START (macOS)"
echo "=========================================="
echo "[1] Qwen3.5-9B"
echo "[2] Qwen2.5-Coder-7B"
read -r -p "Model: " m
case "$m" in
  1) MODEL="$Q35"; NAME="Qwen3.5-9B" ;;
  2) MODEL="$Q25"; NAME="Qwen2.5-Coder-7B" ;;
  *) exit 0 ;;
esac
[[ -f "$MODEL" ]] || { echo "[ERROR] Model not found: $MODEL"; exit 1; }
echo "[1] GPU Server"
echo "[2] CPU Server"
echo "[3] GPU CLI"
echo "[4] CPU CLI"
echo "[5] Back"
read -r -p "Mode: " mode
case "$mode" in
  1) BIN="$GPU/llama-server"; MODE="server" ;;
  2) BIN="$CPU/llama-server"; MODE="server" ;;
  3) BIN="$GPU/llama-cli"; MODE="cli" ;;
  4) BIN="$CPU/llama-cli"; MODE="cli" ;;
  *) exit 0 ;;
esac
[[ -x "$BIN" ]] || { echo "[ERROR] Required binary not found or not executable: $BIN"; exit 1; }
if [[ "$MODE" == "server" ]]; then
  exec "$BIN" -m "$MODEL" -c 16384 --jinja --alias "$NAME"
else
  exec "$BIN" -m "$MODEL" --jinja
fi
