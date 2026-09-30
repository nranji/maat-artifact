#!/usr/bin/env bash
# Install Ollama if needed and pull the two models used in the paper.
#   bash setup_ollama.sh
set -e

PRIMARY="${1:-llama3.2:3b}"
SECONDARY="${2:-llama3.1:8b}"

echo "==> Installing Ollama (if needed)"
if ! command -v ollama >/dev/null 2>&1; then
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        brew install ollama
      else
        echo "Homebrew not found. Download the macOS app from https://ollama.com/download"
        echo "then re-run this script."
        exit 1
      fi
      ;;
    Linux)
      curl -fsSL https://ollama.com/install.sh | sh
      ;;
    *)
      echo "Unsupported OS. See https://ollama.com/download"
      exit 1
      ;;
  esac
else
  echo "    ollama already installed: $(ollama --version 2>/dev/null || true)"
fi

echo "==> Starting the Ollama server (background) if not already running"
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  (ollama serve >/tmp/ollama.log 2>&1 &) || true
  for i in $(seq 1 30); do
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "==> Pulling models: $PRIMARY and $SECONDARY"
ollama pull "$PRIMARY"
ollama pull "$SECONDARY"

echo
echo "Done. Ollama is serving on http://localhost:11434."
echo "Select a model for MAAT with:"
echo "    export MAAT_OLLAMA_MODEL=$PRIMARY    # paper 3B run"
echo "    export MAAT_OLLAMA_MODEL=$SECONDARY  # paper 8B run"
echo "Then, from the repository root:"
echo "    python src/run_all.py --paper --seeds 7,11,13,17,19 --out all"
echo
echo "Committed aggregates in results/ can be inspected without a local LLM."
