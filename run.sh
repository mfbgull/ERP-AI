#!/bin/bash

# ERP AI Assistant - Interactive Setup
# Uses arrow keys + Enter for selection

set -e

# Check for required tools
command -v python3 >/dev/null || { echo "Python3 required"; exit 1; }

# Check LLM providers
OLLAMA_AVAILABLE=false
LLAMA_CPP_AVAILABLE=false

if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_AVAILABLE=true
fi

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    LLAMA_CPP_AVAILABLE=true
fi

# Show banner
clear
echo "╔═══════════════════════════════════════╗"
echo "║       ERP AI Assistant               ║"
echo "╚═══════════════════════════════════════╝"
echo

# No providers available
if [ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ]; then
    echo "ERROR: No LLM providers available!"
    echo
    echo "Please start one of:"
    echo "  - Ollama:    ollama serve"
    echo "  - llama.cpp: ./server -c model.gguf"
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

# Show available providers
echo "Select LLM Provider:"
echo

PROVIDER_OPTIONS=()
PROVIDER_PROMPTS=()

if [ "$OLLAMA_AVAILABLE" = true ]; then
    PROVIDER_OPTIONS+=("ollama")
    PROVIDER_PROMPTS+=("Ollama (local)")
fi

if [ "$LLAMA_CPP_AVAILABLE" = true ]; then
    PROVIDER_OPTIONS+=("llama_cpp")
    PROVIDER_PROMPTS+=("llama.cpp (local)")
fi

# Use select for interactive menu
PS3=$'\x1b[32m➤ Select: \x1b[0m '
select choice in "${PROVIDER_PROMPTS[@]}"; do
    if [ -n "$choice" ]; then
        PROVIDER="${PROVIDER_OPTIONS[$((REPLY-1))]}"
        break
    fi
done 2>/dev/null

echo
echo "Selected: $choice"
echo

# Configure provider in config.yaml
if [ "$PROVIDER" = "ollama" ]; then
    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['ollama']['enabled'] = True
config['llama_cpp']['enabled'] = False
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
"
    echo "Provider: Ollama enabled"
    echo

    # Fetch and select model
    echo "Select Model:"
    echo
    
    curl -s http://localhost:11434/api/tags > /tmp/ollama_models.json
    
    # Read models into array
    mapfile -t MODELS < <(python3 << 'EOF'
import json
with open('/tmp/ollama_models.json') as f:
    data = json.load(f)
for m in data.get('models', []):
    print(m['name'])
EOF
)
    
    if [ ${#MODELS[@]} -eq 0 ]; then
        echo "ERROR: No models found in Ollama"
        exit 1
    fi
    
    # Model selection menu
    PS3=$'\x1b[32m➤ Select: \x1b[0m '
    select choice in "${MODELS[@]}"; do
        if [ -n "$choice" ]; then
            MODEL="$choice"
            break
        fi
    done 2>/dev/null
    
    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['ollama']['model'] = '$MODEL'
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
"
    
    echo
    echo "Selected: $MODEL"
else
    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['ollama']['enabled'] = False
config['llama_cpp']['enabled'] = True
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
"
    echo "Provider: llama.cpp enabled"
fi

echo
echo "═══════════════════════════════════════"
echo
echo "Select App Mode:"
echo

# App mode selection
PS3=$'\x1b[32m➤ Select: \x1b[0m '
select choice in "Web UI (browser)" "CLI (terminal)" "TUI (split panels)"; do
    case $REPLY in
        1) APP="web"; break ;;
        2) APP="cli"; break ;;
        3) APP="tui"; break ;;
    esac
done 2>/dev/null

echo
echo "Selected: $choice"
echo

# Setup virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo "Virtual environment ready"
fi

# Kill any existing process on port 5000
if lsof -ti:5000 >/dev/null 2>&1; then
    echo "Killing existing process on port 5000..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo
echo "═══════════════════════════════════════"
echo

# Launch app
if [ "$APP" = "web" ]; then
    echo "Starting Web UI..."
    echo "Open: http://localhost:5000"
    setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /dev/null 2>&1 &
    sleep 3
    echo "Ready!"
elif [ "$APP" = "tui" ]; then
    echo "Starting TUI..."
    .venv/bin/python tui.py
else
    echo "Starting CLI..."
    .venv/bin/python main.py
fi