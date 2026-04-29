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
    echo "Start Ollama: ollama serve"
    echo "Start llama.cpp: ./server -c model.gguf"
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

PROVIDER_IDX=0
PROVIDER_COUNT=${#PROVIDER_NAMES[@]}

show_provider_menu() {
    clear
    echo "╔═══════════════════════════════════════╗"
    echo "║       ERP AI Assistant               ║"
    echo "╚═══════════════════════════════════════╝"
    echo
    echo "Select LLM Provider:"
    echo
    for i in "${!PROVIDER_NAMES[@]}"; do
        if [ $i -eq $PROVIDER_IDX ]; then
            echo "  ➤ ${PROVIDER_NAMES[$i]}"
        else
            echo "    ${PROVIDER_NAMES[$i]}"
        fi
    done
    echo
    echo "Use ↑/↓ arrows, Enter to select"
}

show_provider_menu

while true; do
    read -rsn1 key
    case "$key" in
        $'\x1b')
            read -rsn1 key
            if [ "$key" = "[" ]; then
                read -rsn1 key
                case "$key" in
                    A)
                        if [ $PROVIDER_IDX -gt 0 ]; then
                            PROVIDER_IDX=$((PROVIDER_IDX - 1))
                        fi
                        ;;
                    B)
                        if [ $PROVIDER_IDX -lt $((PROVIDER_COUNT - 1)) ]; then
                            PROVIDER_IDX=$((PROVIDER_IDX + 1))
                        fi
                        ;;
                esac
            fi
            show_provider_menu
            ;;
        $'\x0d')
            break
            ;;
    esac
done

PROVIDER="${PROVIDER_OPTS[$PROVIDER_IDX]}"
echo
echo "Selected: ${PROVIDER_NAMES[$PROVIDER_IDX]}"

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

    MODEL_OPTS=()
    MODEL_NAMES=()

    while IFS= read -r line; do
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < <(python3 << 'EOF'
import json
with open('/tmp/ollama_models.json') as f:
    data = json.load(f)
for m in data.get('models', []):
    print(m['name'])
EOF
)

    MODEL_IDX=0
    MODEL_COUNT=${#MODEL_NAMES[@]}

    show_model_menu() {
        echo
        echo "Select Model:"
        echo
        for i in "${!MODEL_NAMES[@]}"; do
            if [ $i -eq $MODEL_IDX ]; then
                echo "  ➤ ${MODEL_NAMES[$i]}"
            else
                echo "    ${MODEL_NAMES[$i]}"
            fi
        done
        echo
        echo "Use ↑/↓ arrows, Enter to select"
    }

    show_model_menu

    while true; do
        read -rsn1 key
        case "$key" in
            $'\x1b')
                read -rsn1 key
                if [ "$key" = "[" ]; then
                    read -rsn1 key
                    case "$key" in
                        A)
                            if [ $MODEL_IDX -gt 0 ]; then
                                MODEL_IDX=$((MODEL_IDX - 1))
                            fi
                            ;;
                        B)
                            if [ $MODEL_IDX -lt $((MODEL_COUNT - 1)) ]; then
                                MODEL_IDX=$((MODEL_IDX + 1))
                            fi
                            ;;
                    esac
                fi
                show_model_menu
                ;;
            $'\x0d')
                break
                ;;
        esac
    done

    MODEL="${MODEL_OPTS[$MODEL_IDX]}"

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
echo "═══════════════════════════════"
echo

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")
MODE_IDX=0
MODE_COUNT=3

show_mode_menu() {
    clear
    echo "Select App Mode:"
    echo
    for i in "${!MODE_NAMES[@]}"; do
        if [ $i -eq $MODE_IDX ]; then
            echo "  ➤ ${MODE_NAMES[$i]}"
        else
            echo "    ${MODE_NAMES[$i]}"
        fi
    done
    echo
    echo "Use ↑/↓ arrows, Enter to select"
}

show_mode_menu

while true; do
    read -rsn1 key
    case "$key" in
        $'\x1b')
            read -rsn1 key
            if [ "$key" = "[" ]; then
                read -rsn1 key
                case "$key" in
                    A)
                        if [ $MODE_IDX -gt 0 ]; then
                            MODE_IDX=$((MODE_IDX - 1))
                        fi
                        ;;
                    B)
                        if [ $MODE_IDX -lt $((MODE_COUNT - 1)) ]; then
                            MODE_IDX=$((MODE_IDX + 1))
                        fi
                        ;;
                esac
            fi
            show_mode_menu
            ;;
        $'\x0d')
            break
            ;;
    esac
done

APP="${MODE_OPTS[$MODE_IDX]}"
echo
echo "Selected: ${MODE_NAMES[$MODE_IDX]}"

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
