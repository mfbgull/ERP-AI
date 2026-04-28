#!/bin/bash

set -e

echo "╔═══════════════════════════════════════╗"
echo "║       ERP AI Assistant               ║"
echo "╚═══════════════════════════════════════╝"
echo

OLLAMA_AVAILABLE=false
LLAMA_CPP_AVAILABLE=false

if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_AVAILABLE=true
fi

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    LLAMA_CPP_AVAILABLE=true
fi

echo "Available providers:"
OPTIONS=()
i=1

if [ "$OLLAMA_AVAILABLE" = true ]; then
    echo "  $i. Ollama (local)"
    OPTIONS+=("ollama")
    ((i++))
fi

if [ "$LLAMA_CPP_AVAILABLE" = true ]; then
    echo "  $i. llama.cpp (local)"
    OPTIONS+=("llama_cpp")
    ((i++))
fi

echo

if [ ${#OPTIONS[@]} -eq 0 ]; then
    echo "ERROR: No LLM providers available!"
    echo "  - Ollama: http://localhost:11434"
    echo "  - llama.cpp: http://localhost:8000"
    exit 1
fi

if [ ${#OPTIONS[@]} -eq 1 ]; then
    PROVIDER="${OPTIONS[0]}"
    echo "Using: $PROVIDER (only one available)"
else
    while true; do
        read -p "Select provider: " CHOICE
        if [[ "$CHOICE" =~ ^[0-9]+$ ]] && [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le ${#OPTIONS[@]} ]; then
            PROVIDER="${OPTIONS[$((CHOICE-1))]}"
            break
        fi
        echo "Invalid. Enter 1-${#OPTIONS[@]}"
    done
fi

echo

python3 << EOF
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['ollama']['enabled'] = $([ "$PROVIDER" = "ollama" ] && echo "true" || echo "false")
config['llama_cpp']['enabled'] = $([ "$PROVIDER" = "llama_cpp" ] && echo "true" || echo "false")

with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
EOF

echo "Provider: $PROVIDER enabled"

if [ "$PROVIDER" = "ollama" ]; then
    echo
    echo "Available models:"
    MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "import json,sys; print('\n'.join([m['name'] for m in json.load(sys.stdin).get('models',[])]))" 2>/dev/null || echo "")
    
    if [ -z "$MODELS" ]; then
        echo "  ERROR: Could not fetch models from Ollama"
        exit 1
    fi
    
    echo "$MODELS" | nl -w2 -s "  "
    echo
    
    MODEL_COUNT=$(echo "$MODELS" | wc -l)
    while true; do
        read -p "Select model (number): " CHOICE
        if [[ "$CHOICE" =~ ^[0-9]+$ ]] && [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le "$MODEL_COUNT" ]; then
            MODEL=$(echo "$MODELS" | sed -n "${CHOICE}p")
            break
        fi
        echo "Invalid. Enter 1-$MODEL_COUNT"
    done
    
    echo
    
    python3 << EOF
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

config['ollama']['model'] = '$MODEL'

with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
EOF
    
    echo "Model: $MODEL selected"
fi

echo
echo "═══════════════════════════════════════"
echo "Select app mode:"
echo "  1. Web UI (browser)"
echo "  2. CLI (terminal)"
echo

while true; do
    read -p "Choice: " MODE_CHOICE
    case $MODE_CHOICE in
        1) APP="web"; break ;;
        2) APP="cli"; break ;;
        *) echo "Invalid. Enter 1 or 2" ;;
    esac
done

echo

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

if [ "$APP" = "web" ]; then
    echo "Starting Web UI..."
    echo "🌐 Open: http://localhost:5000"
    .venv/bin/python web.py
else
    echo "Starting CLI..."
    .venv/bin/python main.py
fi