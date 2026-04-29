#!/bin/bash

check_ollama() {
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1
}

check_llamacpp() {
    curl -s http://localhost:8000/health >/dev/null 2>&1
}

if check_ollama; then OLLAMA_AVAILABLE=true; else OLLAMA_AVAILABLE=false; fi
if check_llamacpp; then LLAMA_CPP_AVAILABLE=true; else LLAMA_CPP_AVAILABLE=false; fi

clear
echo "╔═══════════════════════════════════════╗"
echo "║       ERP AI Assistant               ║"
echo "╚═══════════════════════════════════════╝"
echo

[ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ] && {
    echo "ERROR: No LLM providers available!"
    read -p "Press Enter to exit..."
    exit 1
}

PROVIDER_OPTS=()
PROVIDER_NAMES=()
[ "$OLLAMA_AVAILABLE" = true ] && { PROVIDER_OPTS+=("ollama"); PROVIDER_NAMES+=("Ollama (local)"); }
[ "$LLAMA_CPP_AVAILABLE" = true ] && { PROVIDER_OPTS+=("llama_cpp"); PROVIDER_NAMES+=("llama.cpp (local)"); }

stty -echo echonl 2>/dev/null

draw_provider_menu() {
    clear
    echo "╔═══════════════════════════════════════╗"
    echo "║       ERP AI Assistant               ║"
    echo "╚═══════════════════════════════════════╝"
    echo
    echo "Select LLM Provider:"
    echo
    i=0
    for name in "${PROVIDER_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo "  ➤ $name"; else echo "    $name"; fi
        i=$((i+1))
    done
    echo
    echo "↑↓ arrows to move, Enter to select"
}

cur=0
count=${#PROVIDER_NAMES[@]}
draw_provider_menu

while true; do
    key=$(dd bs=1 count=1 2>/dev/null)
    code=$(printf '%d' "'$key")
    
    if [ "$code" -eq 27 ]; then
        dd bs=1 count=1 2>/dev/null
        dd bs=1 count=1 2>/dev/null
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key")
        
        if [ "$code" -eq 65 ]; then
            cur=$((cur - 1 < 0 ? 0 : cur - 1))
            draw_provider_menu
        elif [ "$code" -eq 66 ]; then
            cur=$((cur + 1 >= count ? count - 1 : cur + 1))
            draw_provider_menu
        fi
    elif [ "$code" -eq 10 ]; then
        break
    fi
done

stty sane 2>/dev/null
echo
echo "Selected: ${PROVIDER_NAMES[$cur]}"
PROVIDER="${PROVIDER_OPTS[$cur]}"
echo

[ "$PROVIDER" = "ollama" ] && {
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
    python3 -c "
import json
with open('/tmp/ollama_models.json') as f:
    data = json.load(f)
models = [m['name'] for m in data.get('models', [])]
with open('/tmp/model_list.txt', 'w') as f:
    f.write('\n'.join(models))
"

    MODEL_OPTS=()
    MODEL_NAMES=()
    while IFS= read -r line; do
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < /tmp/model_list.txt

    stty -echo echonl 2>/dev/null
    
    draw_model_menu() {
        echo "Select Model:"
        echo
        i=0
        for name in "${MODEL_NAMES[@]}"; do
            if [ $i -eq $cur ]; then echo "  ➤ $name"; else echo "    $name"; fi
            i=$((i+1))
        done
        echo
        echo "↑↓ arrows to move, Enter to select"
    }

    cur=0
    count=${#MODEL_NAMES[@]}
    draw_model_menu

    while true; do
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key")
        
        if [ "$code" -eq 27 ]; then
            dd bs=1 count=1 2>/dev/null
            dd bs=1 count=1 2>/dev/null
            key=$(dd bs=1 count=1 2>/dev/null)
            code=$(printf '%d' "'$key")
            
            if [ "$code" -eq 65 ]; then
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_model_menu
            elif [ "$code" -eq 66 ]; then
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_model_menu
            fi
        elif [ "$code" -eq 10 ]; then
            break
        fi
    done

    stty sane 2>/dev/null
    echo
    echo "Selected: ${MODEL_NAMES[$cur]}"
    MODEL="${MODEL_OPTS[$cur]}"

    python3 -c "
import yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['ollama']['model'] = '$MODEL'
with open('config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
"
} || {
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
}

echo
echo "═══════════════════════════════════════"
echo

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")

stty -echo echonl 2>/dev/null

draw_mode_menu() {
    echo "Select App Mode:"
    echo
    i=0
    for name in "${MODE_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo "  ➤ $name"; else echo "    $name"; fi
        i=$((i+1))
    done
    echo
    echo "↑↓ arrows to move, Enter to select"
}

cur=0
count=3
draw_mode_menu

while true; do
    key=$(dd bs=1 count=1 2>/dev/null)
    code=$(printf '%d' "'$key")
    
    if [ "$code" -eq 27 ]; then
        dd bs=1 count=1 2>/dev/null
        dd bs=1 count=1 2>/dev/null
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key")
        
        if [ "$code" -eq 65 ]; then
            cur=$((cur - 1 < 0 ? 0 : cur - 1))
            draw_mode_menu
        elif [ "$code" -eq 66 ]; then
            cur=$((cur + 1 >= count ? count - 1 : cur + 1))
            draw_mode_menu
        fi
    elif [ "$code" -eq 10 ]; then
        break
    fi
done

stty sane 2>/dev/null
echo
echo "Selected: ${MODE_NAMES[$cur]}"
APP="${MODE_OPTS[$cur]}"
echo

[ ! -d ".venv" ] && {
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    echo "Virtual environment ready"
}

lsof -ti:5000 >/dev/null 2>&1 && {
    echo "Killing existing on port 5000..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
}
echo

[ "$APP" = "web" ] && {
    echo "Starting Web UI..."
    echo "Open: http://localhost:5000"
    setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /dev/null 2>&1 &
    sleep 3
    echo "Ready!"
}
[ "$APP" = "tui" ] && {
    echo "Starting TUI..."
    .venv/bin/python tui.py
}
[ "$APP" = "cli" ] && {
    echo "Starting CLI..."
    .venv/bin/python main.py
}