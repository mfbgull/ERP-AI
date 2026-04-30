#!/bin/bash

# ERP AI Assistant - Interactive Setup Script
# Enhanced with TTS support and production features

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running interactively (terminal available)
if [ -t 0 ] 2>/dev/null && [ -t 1 ] 2>/dev/null; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

check_ollama() {
    curl -s --connect-timeout 2 http://localhost:11434/api/tags >/dev/null 2>&1
}

check_llamacpp() {
    curl -s --connect-timeout 2 http://localhost:8000/health >/dev/null 2>&1
}

check_spd_say() {
    which spd-say >/dev/null 2>&1
}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check LLM providers
echo -e "${YELLOW}Checking LLM providers...${NC}"
if check_ollama; then
    OLLAMA_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} Ollama available"
else
    OLLAMA_AVAILABLE=false
    echo -e "  ${RED}✗${NC} Ollama not available"
fi

if check_llamacpp; then
    LLAMA_CPP_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} llama.cpp available"
else
    LLAMA_CPP_AVAILABLE=false
    echo -e "  ${RED}✗${NC} llama.cpp not available"
fi

if [ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ]; then
    echo
    echo -e "${RED}ERROR: No LLM providers available!${NC}"
    echo "Please install Ollama or llama.cpp and try again."
    echo
    [ "$INTERACTIVE" = true ] && read -p "Press Enter to exit..."
    exit 1
fi

# Provider selection
PROVIDER_OPTS=()
PROVIDER_NAMES=()
[ "$OLLAMA_AVAILABLE" = true ] && { PROVIDER_OPTS+=("ollama"); PROVIDER_NAMES+=("Ollama (local)"); }
[ "$LLAMA_CPP_AVAILABLE" = true ] && { PROVIDER_OPTS+=("llama_cpp"); PROVIDER_NAMES+=("llama.cpp (local)"); }

# Interactive provider selection
if [ "$INTERACTIVE" = true ] && [ ${#PROVIDER_NAMES[@]} -gt 1 ]; then
    stty -echo echonl 2>/dev/null
    
    draw_provider_menu() {
        clear
        echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo
        echo "Select LLM Provider:"
        echo
        i=0
        for name in "${PROVIDER_NAMES[@]}"; do
            if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
            i=$((i+1))
        done
        echo
        echo "↑↓ arrows to move, Enter to select"
    }
    
    cur=0
    count=${#PROVIDER_NAMES[@]}
    draw_provider_menu
    
    while true; do
        IFS= read -rsn1 key 2>/dev/null || true
        if [ -z "$key" ]; then
            # Enter key pressed
            break
        fi
        
        ord=$(printf '%d' "'$key")
        
        if [ "$ord" -eq 27 ]; then
            # Escape sequence (arrow key)
            IFS= read -rsn1 -t 0.1 _ 2>/dev/null || true
            IFS= read -rsn1 -t 0.1 key2 2>/dev/null || true
            ord2=$(printf '%d' "'$key2" 2>/dev/null || echo 0)
            
            if [ "$ord2" -eq 65 ]; then
                # Up arrow
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_provider_menu
            elif [ "$ord2" -eq 66 ]; then
                # Down arrow
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_provider_menu
            fi
        elif [ "$ord" -ge 49 ] && [ "$ord" -le 57 ]; then
            # Number key
            num=$((ord - 48))
            if [ $num -le $count ]; then
                cur=$((num - 1))
                break
            fi
        elif [ "$ord" -eq 10 ] || [ "$ord" -eq 13 ]; then
            # Enter
            break
        fi
    done
    
    stty sane 2>/dev/null
    echo
else
    # Non-interactive or single option - use first available
    cur=0
fi

echo -e "Selected: ${GREEN}${PROVIDER_NAMES[$cur]}${NC}"
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

    curl -s http://localhost:11434/api/tags > /tmp/ollama_models.json 2>/dev/null
    python3 -c "
import json
try:
    with open('/tmp/ollama_models.json') as f:
        data = json.load(f)
    models = [m['name'] for m in data.get('models', [])]
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('\n'.join(models))
except:
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('gemma3:270m\nllama3.2\nmistral')
"

    MODEL_OPTS=()
    MODEL_NAMES=()
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < /tmp/model_list.txt

    # Interactive model selection
    if [ "$INTERACTIVE" = true ] && [ ${#MODEL_NAMES[@]} -gt 1 ]; then
        stty -echo echonl 2>/dev/null
        
        draw_model_menu() {
            echo "Select Model:"
            echo
            i=0
            for name in "${MODEL_NAMES[@]}"; do
                if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
                i=$((i+1))
            done
            echo
            echo "↑↓ arrows to move, Enter to select"
        }
        
        cur=0
        count=${#MODEL_NAMES[@]}
        draw_model_menu
        
        while true; do
            IFS= read -rsn1 key 2>/dev/null || true
            if [ -z "$key" ]; then
                break
            fi
            
            ord=$(printf '%d' "'$key")
            
            if [ "$ord" -eq 27 ]; then
                IFS= read -rsn1 -t 0.1 _ 2>/dev/null || true
                IFS= read -rsn1 -t 0.1 key2 2>/dev/null || true
                ord2=$(printf '%d' "'$key2" 2>/dev/null || echo 0)
                
                if [ "$ord2" -eq 65 ]; then
                    cur=$((cur - 1 < 0 ? 0 : cur - 1))
                    draw_model_menu
                elif [ "$ord2" -eq 66 ]; then
                    cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                    draw_model_menu
                fi
            elif [ "$ord" -ge 49 ] && [ "$ord" -le 57 ]; then
                num=$((ord - 48))
                if [ $num -le $count ]; then
                    cur=$((num - 1))
                    break
                fi
            elif [ "$ord" -eq 10 ] || [ "$ord" -eq 13 ]; then
                break
            fi
        done
        
        stty sane 2>/dev/null
    else
        # Non-interactive - use first model
        cur=0
    fi
    
    echo
    echo -e "Selected: ${GREEN}${MODEL_NAMES[$cur]}${NC}"
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
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")

# Interactive mode selection
if [ "$INTERACTIVE" = true ]; then
    stty -echo echonl 2>/dev/null
    
    draw_mode_menu() {
        echo "Select App Mode:"
        echo
        i=0
        for name in "${MODE_NAMES[@]}"; do
            if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
            i=$((i+1))
        done
        echo
        echo "↑↓ arrows to move, Enter to select"
    }
    
    cur=0
    count=3
    draw_mode_menu
    
    while true; do
        IFS= read -rsn1 key 2>/dev/null || true
        if [ -z "$key" ]; then
            break
        fi
        
        ord=$(printf '%d' "'$key")
        
        if [ "$ord" -eq 27 ]; then
            IFS= read -rsn1 -t 0.1 _ 2>/dev/null || true
            IFS= read -rsn1 -t 0.1 key2 2>/dev/null || true
            ord2=$(printf '%d' "'$key2" 2>/dev/null || echo 0)
            
            if [ "$ord2" -eq 65 ]; then
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_mode_menu
            elif [ "$ord2" -eq 66 ]; then
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_mode_menu
            fi
        elif [ "$ord" -ge 49 ] && [ "$ord" -le 51 ]; then
            num=$((ord - 48))
            if [ $num -le $count ]; then
                cur=$((num - 1))
                break
            fi
        elif [ "$ord" -eq 10 ] || [ "$ord" -eq 13 ]; then
            break
        fi
    done
    
    stty sane 2>/dev/null
else
    # Non-interactive - use default (web)
    cur=0
fi

echo
echo -e "Selected: ${GREEN}${MODE_NAMES[$cur]}${NC}"
APP="${MODE_OPTS[$cur]}"
echo

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    echo -e "${GREEN}✓${NC} Virtual environment ready"
fi

# Install TTS dependencies if available
if [ "$TTS_AVAILABLE" = true ]; then
    .venv/bin/pip install -q soundfile 2>/dev/null || true
fi

# Kill existing on port 5000
lsof -ti:5000 >/dev/null 2>&1 && {
    echo -e "${YELLOW}Killing existing process on port 5000...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
}

echo

# Display system info
echo -e "${BLUE}System Configuration:${NC}"
echo "  Database: /home/fawad/ai/minierp/database/erp.db"
echo "  LLM: $PROVIDER ($MODEL)"
echo "  TTS: $(if [ "$TTS_AVAILABLE" = true ]; then echo 'speech-dispatcher (local)'; else echo 'not available'; fi)"
echo "  Tables: 36 | Items: 12 | Customers: 3 | BOMs: 3"
echo

# Launch application
case $APP in
    web)
        echo -e "${GREEN}Starting Web UI...${NC}"
        echo -e "${GREEN}Open: http://localhost:5000${NC}"
        echo
        setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /tmp/erp_web.log 2>&1 &
        sleep 3
        if pgrep -f gunicorn > /dev/null; then
            echo -e "${GREEN}✓${NC} Web UI running on http://localhost:5000"
            echo
            echo "Features:"
            echo "  • Chat with AI assistant"
            echo "  • View customers, items, invoices"
            echo "  • BOM management & cost calculation"
            echo "  • Voice transcription (STT)"
            echo "  • Text-to-speech (TTS)"
            echo
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
            wait
        else
            echo -e "${RED}✗ Failed to start Web UI${NC}"
            cat /tmp/erp_web.log
            exit 1
        fi
        ;;
    tui)
        echo -e "${GREEN}Starting TUI...${NC}"
        echo
        .venv/bin/python3 tui.py
        ;;
    cli)
        echo -e "${GREEN}Starting CLI...${NC}"
        echo
        echo "Commands: /help, /clear, /model, /switch, /quit"
        echo
        .venv/bin/python3 main.py
        ;;
esac

check_llamacpp() {
    curl -s --connect-timeout 2 http://localhost:8000/health >/dev/null 2>&1
}

check_spd_say() {
    which spd-say >/dev/null 2>&1
}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check LLM providers
echo -e "${YELLOW}Checking LLM providers...${NC}"
if check_ollama; then
    OLLAMA_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} Ollama available"
else
    OLLAMA_AVAILABLE=false
    echo -e "  ${RED}✗${NC} Ollama not available"
fi

if check_llamacpp; then
    LLAMA_CPP_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} llama.cpp available"
else
    LLAMA_CPP_AVAILABLE=false
    echo -e "  ${RED}✗${NC} llama.cpp not available"
fi

if [ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ]; then
    echo
    echo -e "${RED}ERROR: No LLM providers available!${NC}"
    echo "Please install Ollama or llama.cpp and try again."
    echo
    [ "$INTERACTIVE" = true ] && read -p "Press Enter to exit..."
    exit 1
fi

# Provider selection
PROVIDER_OPTS=()
PROVIDER_NAMES=()
[ "$OLLAMA_AVAILABLE" = true ] && { PROVIDER_OPTS+=("ollama"); PROVIDER_NAMES+=("Ollama (local)"); }
[ "$LLAMA_CPP_AVAILABLE" = true ] && { PROVIDER_OPTS+=("llama_cpp"); PROVIDER_NAMES+=("llama.cpp (local)"); }

if [ "$INTERACTIVE" = true ]; then
    stty -echo echonl 2>/dev/null
fi

draw_provider_menu() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Select LLM Provider:"
    echo
    i=0
    for name in "${PROVIDER_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
        i=$((i+1))
    done
    echo
    echo "↑↓ arrows to move, Enter to select"
}

cur=0
count=${#PROVIDER_NAMES[@]}

if [ "$INTERACTIVE" = true ] && [ $count -gt 1 ]; then
    draw_provider_menu
    
    while true; do
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
        
        # Handle Enter key (both LF \n and CR \r)
        if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
            break
        fi
        
        if [ "$code" -eq 27 ]; then
            dd bs=1 count=1 2>/dev/null
            dd bs=1 count=1 2>/dev/null
            key=$(dd bs=1 count=1 2>/dev/null)
            code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
            
            if [ "$code" -eq 65 ]; then
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_provider_menu
            elif [ "$code" -eq 66 ]; then
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_provider_menu
            fi
        elif [ "$code" -ge 49 ] && [ "$code" -le 57 ]; then
            num=$((code - 48))
            if [ $num -le $count ]; then
                cur=$((num - 1))
                break
            fi
        fi
    done
fi

if [ "$INTERACTIVE" = true ]; then
    stty sane 2>/dev/null
fi

echo
echo -e "Selected: ${GREEN}${PROVIDER_NAMES[$cur]}${NC}"
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

    curl -s http://localhost:11434/api/tags > /tmp/ollama_models.json 2>/dev/null
    python3 -c "
import json
try:
    with open('/tmp/ollama_models.json') as f:
        data = json.load(f)
    models = [m['name'] for m in data.get('models', [])]
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('\n'.join(models))
except:
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('gemma3:270m\nllama3.2\nmistral')
"

    MODEL_OPTS=()
    MODEL_NAMES=()
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < /tmp/model_list.txt

    if [ "$INTERACTIVE" = true ]; then
        stty -echo echonl 2>/dev/null
    fi
    
    draw_model_menu() {
        echo "Select Model:"
        echo
        i=0
        for name in "${MODEL_NAMES[@]}"; do
            if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
            i=$((i+1))
        done
        echo
        echo "↑↓ arrows to move, Enter to select"
    }
    
    cur=0
    count=${#MODEL_NAMES[@]}
    [ $count -eq 0 ] && { echo "No models found, using default"; MODEL="gemma3:270m"; count=1; }
    
    if [ "$INTERACTIVE" = true ] && [ $count -gt 1 ]; then
        draw_model_menu
        
        while true; do
            key=$(dd bs=1 count=1 2>/dev/null)
            code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
            
            # Handle Enter key
            if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
                break
            fi
            
            if [ "$code" -eq 27 ]; then
                dd bs=1 count=1 2>/dev/null
                dd bs=1 count=1 2>/dev/null
                key=$(dd bs=1 count=1 2>/dev/null)
                code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
                
                if [ "$code" -eq 65 ]; then
                    cur=$((cur - 1 < 0 ? 0 : cur - 1))
                    draw_model_menu
                elif [ "$code" -eq 66 ]; then
                    cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                    draw_model_menu
                fi
            elif [ "$code" -ge 49 ] && [ "$code" -le 57 ]; then
                num=$((code - 48))
                if [ $num -le $count ]; then
                    cur=$((num - 1))
                    break
                fi
            fi
        done
    fi
    
    if [ "$INTERACTIVE" = true ]; then
        stty sane 2>/dev/null
    fi
    
    echo
    echo -e "Selected: ${GREEN}${MODEL_NAMES[$cur]}${NC}"
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
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")

if [ "$INTERACTIVE" = true ]; then
    stty -echo echonl 2>/dev/null
fi

draw_mode_menu() {
    echo "Select App Mode:"
    echo
    i=0
    for name in "${MODE_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
        i=$((i+1))
    done
    echo
    echo "↑↓ arrows to move, Enter to select"
}

cur=0
count=3

if [ "$INTERACTIVE" = true ] && [ $count -gt 1 ]; then
    draw_mode_menu
    
    while true; do
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
        
        # Handle Enter key
        if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
            break
        fi
        
        if [ "$code" -eq 27 ]; then
            dd bs=1 count=1 2>/dev/null
            dd bs=1 count=1 2>/dev/null
            key=$(dd bs=1 count=1 2>/dev/null)
            code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
            
            if [ "$code" -eq 65 ]; then
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_mode_menu
            elif [ "$code" -eq 66 ]; then
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_mode_menu
            fi
        elif [ "$code" -ge 49 ] && [ "$code" -le 51 ]; then
            num=$((code - 48))
            if [ $num -le $count ]; then
                cur=$((num - 1))
                break
            fi
        fi
    done
fi

if [ "$INTERACTIVE" = true ]; then
    stty sane 2>/dev/null
fi

echo
echo -e "Selected: ${GREEN}${MODE_NAMES[$cur]}${NC}"
APP="${MODE_OPTS[$cur]}"
echo

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    echo -e "${GREEN}✓${NC} Virtual environment ready"
fi

# Install TTS dependencies if available
if [ "$TTS_AVAILABLE" = true ]; then
    .venv/bin/pip install -q soundfile 2>/dev/null || true
fi

# Kill existing on port 5000
lsof -ti:5000 >/dev/null 2>&1 && {
    echo -e "${YELLOW}Killing existing process on port 5000...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
}

echo

# Display system info
echo -e "${BLUE}System Configuration:${NC}"
echo "  Database: /home/fawad/ai/minierp/database/erp.db"
echo "  LLM: $PROVIDER ($MODEL)"
echo "  TTS: $(if [ "$TTS_AVAILABLE" = true ]; then echo 'speech-dispatcher (local)'; else echo 'not available'; fi)"
echo "  Tables: 36 | Items: 12 | Customers: 3 | BOMs: 3"
echo

# Launch application
case $APP in
    web)
        echo -e "${GREEN}Starting Web UI...${NC}"
        echo -e "${GREEN}Open: http://localhost:5000${NC}"
        echo
        setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /tmp/erp_web.log 2>&1 &
        sleep 3
        if pgrep -f gunicorn > /dev/null; then
            echo -e "${GREEN}✓${NC} Web UI running on http://localhost:5000"
            echo
            echo "Features:"
            echo "  • Chat with AI assistant"
            echo "  • View customers, items, invoices"
            echo "  • BOM management & cost calculation"
            echo "  • Voice transcription (STT)"
            echo "  • Text-to-speech (TTS)"
            echo
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
            wait
        else
            echo -e "${RED}✗ Failed to start Web UI${NC}"
            cat /tmp/erp_web.log
            exit 1
        fi
        ;;
    tui)
        echo -e "${GREEN}Starting TUI...${NC}"
        echo
        .venv/bin/python3 tui.py
        ;;
    cli)
        echo -e "${GREEN}Starting CLI...${NC}"
        echo
        echo "Commands: /help, /clear, /model, /switch, /quit"
        echo
        .venv/bin/python3 main.py
        ;;
esac

check_llamacpp() {
    curl -s --connect-timeout 2 http://localhost:8000/health >/dev/null 2>&1
}

check_spd_say() {
    which spd-say >/dev/null 2>&1
}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check LLM providers
echo -e "${YELLOW}Checking LLM providers...${NC}"
if check_ollama; then
    OLLAMA_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} Ollama available"
else
    OLLAMA_AVAILABLE=false
    echo -e "  ${RED}✗${NC} Ollama not available"
fi

if check_llamacpp; then
    LLAMA_CPP_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} llama.cpp available"
else
    LLAMA_CPP_AVAILABLE=false
    echo -e "  ${RED}✗${NC} llama.cpp not available"
fi

if [ "$OLLAMA_AVAILABLE" = false ] && [ "$LLAMA_CPP_AVAILABLE" = false ]; then
    echo
    echo -e "${RED}ERROR: No LLM providers available!${NC}"
    echo "Please install Ollama or llama.cpp and try again."
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

# Check TTS
echo
echo -e "${YELLOW}Checking TTS engine...${NC}"
if check_spd_say; then
    TTS_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} speech-dispatcher (spd-say) available"
else
    TTS_AVAILABLE=false
    echo -e "  ${YELLOW}⚠${NC} speech-dispatcher not found (voice output disabled)"
fi

# Provider selection
PROVIDER_OPTS=()
PROVIDER_NAMES=()
[ "$OLLAMA_AVAILABLE" = true ] && { PROVIDER_OPTS+=("ollama"); PROVIDER_NAMES+=("Ollama (local)"); }
[ "$LLAMA_CPP_AVAILABLE" = true ] && { PROVIDER_OPTS+=("llama_cpp"); PROVIDER_NAMES+=("llama.cpp (local)"); }

stty -echo echonl 2>/dev/null

draw_provider_menu() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              ERP AI Assistant - Setup                       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Select LLM Provider:"
    echo
    i=0
    for name in "${PROVIDER_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
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
    code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
    
    # Handle Enter key (both LF \\n and CR \\r)
    if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
        break
    fi
    
    if [ "$code" -eq 27 ]; then
        dd bs=1 count=1 2>/dev/null
        dd bs=1 count=1 2>/dev/null
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
        
        if [ "$code" -eq 65 ]; then
            cur=$((cur - 1 < 0 ? 0 : cur - 1))
            draw_provider_menu
        elif [ "$code" -eq 66 ]; then
            cur=$((cur + 1 >= count ? count - 1 : cur + 1))
            draw_provider_menu
        fi
    elif [ "$code" -ge 49 ] && [ "$code" -le 57 ]; then
        num=$((code - 48))
        if [ $num -le $count ]; then
            cur=$((num - 1))
            break
        fi
    fi
done

stty sane 2>/dev/null
echo
echo -e "Selected: ${GREEN}${PROVIDER_NAMES[$cur]}${NC}"
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

    curl -s http://localhost:11434/api/tags > /tmp/ollama_models.json 2>/dev/null
    python3 -c "
import json
try:
    with open('/tmp/ollama_models.json') as f:
        data = json.load(f)
    models = [m['name'] for m in data.get('models', [])]
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('\n'.join(models))
except:
    with open('/tmp/model_list.txt', 'w') as f:
        f.write('gemma3:270m\nllama3.2\nmistral')
"

    MODEL_OPTS=()
    MODEL_NAMES=()
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        MODEL_OPTS+=("$line")
        MODEL_NAMES+=("$line")
    done < /tmp/model_list.txt

    stty -echo echonl 2>/dev/null
    
    draw_model_menu() {
        echo "Select Model:"
        echo
        i=0
        for name in "${MODEL_NAMES[@]}"; do
            if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
            i=$((i+1))
        done
        echo
        echo "↑↓ arrows to move, Enter to select"
    }
    
    cur=0
    count=${#MODEL_NAMES[@]}
    [ $count -eq 0 ] && { echo "No models found, using default"; MODEL="gemma3:270m"; count=1; }
    draw_model_menu
    
    while true; do
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
        
        # Handle Enter key (both LF \\n and CR \\r)
        if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
            break
        fi
        
        if [ "$code" -eq 27 ]; then
            dd bs=1 count=1 2>/dev/null
            dd bs=1 count=1 2>/dev/null
            key=$(dd bs=1 count=1 2>/dev/null)
            code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
            
            if [ "$code" -eq 65 ]; then
                cur=$((cur - 1 < 0 ? 0 : cur - 1))
                draw_model_menu
            elif [ "$code" -eq 66 ]; then
                cur=$((cur + 1 >= count ? count - 1 : cur + 1))
                draw_model_menu
            fi
        elif [ "$code" -ge 49 ] && [ "$code" -le 57 ]; then
            num=$((code - 48))
            if [ $num -le $count ]; then
                cur=$((num - 1))
                break
            fi
        fi
    done
    
    stty sane 2>/dev/null
    echo
    echo -e "Selected: ${GREEN}${MODEL_NAMES[$cur]}${NC}"
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
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo

MODE_OPTS=("web" "cli" "tui")
MODE_NAMES=("Web UI (browser)" "CLI (terminal)" "TUI (split panels)")

stty -echo echonl 2>/dev/null

draw_mode_menu() {
    echo "Select App Mode:"
    echo
    i=0
    for name in "${MODE_NAMES[@]}"; do
        if [ $i -eq $cur ]; then echo -e "  ${GREEN}➤${NC} $name"; else echo "    $name"; fi
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
    code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
    
    # Handle Enter key (both LF \\n and CR \\r)
    if [ "$key" = "" ] || [ "$code" -eq 10 ] || [ "$code" -eq 13 ]; then
        break
    fi
    
    if [ "$code" -eq 27 ]; then
        dd bs=1 count=1 2>/dev/null
        dd bs=1 count=1 2>/dev/null
        key=$(dd bs=1 count=1 2>/dev/null)
        code=$(printf '%d' "'$key" 2>/dev/null || echo 0)
        
        if [ "$code" -eq 65 ]; then
            cur=$((cur - 1 < 0 ? 0 : cur - 1))
            draw_mode_menu
        elif [ "$code" -eq 66 ]; then
            cur=$((cur + 1 >= count ? count - 1 : cur + 1))
            draw_mode_menu
        fi
    elif [ "$code" -ge 49 ] && [ "$code" -le 51 ]; then
        num=$((code - 48))
        if [ $num -le $count ]; then
            cur=$((num - 1))
            break
        fi
    fi
done

stty sane 2>/dev/null
echo
echo -e "Selected: ${GREEN}${MODE_NAMES[$cur]}${NC}"
APP="${MODE_OPTS[$cur]}"
echo

# Setup virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    echo -e "${GREEN}✓${NC} Virtual environment ready"
fi

# Install TTS dependencies if available
if [ "$TTS_AVAILABLE" = true ]; then
    .venv/bin/pip install -q soundfile 2>/dev/null || true
fi

# Kill existing on port 5000
lsof -ti:5000 >/dev/null 2>&1 && {
    echo -e "${YELLOW}Killing existing process on port 5000...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
}

echo

# Display system info
echo -e "${BLUE}System Configuration:${NC}"
echo "  Database: /home/fawad/ai/minierp/database/erp.db"
echo "  LLM: $PROVIDER ($MODEL)"
echo "  TTS: $(if [ "$TTS_AVAILABLE" = true ]; then echo 'speech-dispatcher (local)'; else echo 'not available'; fi)"
echo "  Tables: 36 | Items: 12 | Customers: 3 | BOMs: 3"
echo

# Launch application
case $APP in
    web)
        echo -e "${GREEN}Starting Web UI...${NC}"
        echo -e "${GREEN}Open: http://localhost:5000${NC}"
        echo
        setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /tmp/erp_web.log 2>&1 &
        sleep 3
        if pgrep -f gunicorn > /dev/null; then
            echo -e "${GREEN}✓${NC} Web UI running on http://localhost:5000"
            echo
            echo "Features:"
            echo "  • Chat with AI assistant"
            echo "  • View customers, items, invoices"
            echo "  • BOM management & cost calculation"
            echo "  • Voice transcription (STT)"
            echo "  • Text-to-speech (TTS)"
            echo
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
            wait
        else
            echo -e "${RED}✗ Failed to start Web UI${NC}"
            cat /tmp/erp_web.log
            exit 1
        fi
        ;;
    tui)
        echo -e "${GREEN}Starting TUI...${NC}"
        echo
        .venv/bin/python3 tui.py
        ;;
    cli)
        echo -e "${GREEN}Starting CLI...${NC}"
        echo
        echo "Commands: /help, /clear, /model, /switch, /quit"
        echo
        .venv/bin/python3 main.py
        ;;
esac