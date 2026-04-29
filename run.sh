#!/bin/bash
set -e

OLLAMA_AVAILABLE=false
LLAMA_CPP_AVAILABLE=false

if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_AVAILABLE=true
fi

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    LLAMA_CPP_AVAILABLE=true
fi

clear
echo "╔═══════════════════════════════════════╗"
echo "║       ERP AI Assistant               ║"
echo "╚═══════════════════════════════════════╝"
echo

if [ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ]; then
    echo "ERROR: No LLM providers available!"
    read -p "Press Enter to exit..."
    exit 1
fi

PROVIDER_OPTS=()
PROVIDER_NAMES=()

if [ "$OLLAMA_AVAILABLE" = true ]; then
    PROVIDER_OPTS+=("ollama")
    PROVIDER_NAMES+=("Ollama (local)")
fi

if [ "$LLAMA_CPP_AVAILABLE" = true ]; then
    PROVIDER_OPTS+=("llama_cpp")
    PROVIDER_NAMES+=("llama.cpp (local)")
fi

echo "Select LLM Provider:"
echo
PS3="➤ "
select choice in "${PROVIDER_NAMES[@]}"; do
    if [ -n "$choice" ]; then
        PROVIDER_IDX=$((REPLY - 1))
        break
    fi
done 2>/dev/null || PROVIDER_IDX=0

echo "Selected: ${PROVIDER_NAMES[$PROVIDER_IDX]}"
PROVIDER="${PROVIDER_OPTS[$PROVIDER_IDX]}"
echo

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

    curl -s http://localhost:11434/api/tags > /tmp/ollama_models.json
    python3 << 'PYEOF'
import json
with open('/tmp/ollama_models.json') as f:
    data = json.load(f)
models = [m['name'] for m in data.get('models', [])]
with open('/tmp/model_list.txt', 'w') as f:
    f.write('\n'.join(models))
print(len(models))
PYEOF

    MODEL_OPTS=()
    MODEL_NAMES=()
    while IFS= read -r line; do
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < /tmp/model_list.txt

    echo "Select Model:"
    echo
    PS3="➤ "
    select choice in "${MODEL_NAMES[@]}"; do
        if [ -n "$choice" ]; then
            MODEL_IDX=$((REPLY - 1))
            break
        fi
    done 2>/dev/null || MODEL_IDX=0

    echo "Selected: ${MODEL_NAMES[$MODEL_IDX]}"
    MODEL="${MODEL_OPTS[$MODEL_IDX]}"

    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['ollama']['model'] = '$MODEL'
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
"
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

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")

echo "Select App Mode:"
echo
PS3="➤ "
select choice in "${MODE_NAMES[@]}"; do
    if [ -n "$choice" ]; then
        MODE_IDX=$((REPLY - 1))
        break
    fi
done 2>/dev/null || MODE_IDX=0

echo "Selected: ${MODE_NAMES[$MODE_IDX]}"
APP="${MODE_OPTS[$MODE_IDX]}"
echo

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo "Virtual environment ready"
fi

if lsof -ti:5000 >/dev/null 2>&1; then
    echo "Killing existing on port 5000..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo

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
