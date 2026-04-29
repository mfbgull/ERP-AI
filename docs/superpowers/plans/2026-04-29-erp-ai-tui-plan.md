# ERP AI TUI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a terminal-based TUI for ERP AI with split panels (chat/data), ANSI color theming, and command palette.

**Architecture:** Split-panel layout using ANSI escape codes. No external TUI libraries - pure Python standard library with curses/ncurses for terminal control.

**Tech Stack:** Python 3.8+, standard library (curses/ansi), Flask (existing), SQLite (existing)

---

## Chunk 1: TUI Core Module

### Task 1: Create TUI Module

**Files:**
- Create: `tui.py` (new main module)
- Modify: `run.sh` (add TUI mode option)

**Files to read before writing:**
- `main.py` (lines 1-50): Understand imports and startup
- `core/config.py`: Load config
- `core/llm_handler.py`: LLM handling
- `core/operations.py`: Operations
- `core/conversation.py`: Conversation engine

- [ ] **Step 1: Create tui.py skeleton with imports**

```python
#!/usr/bin/env python3
"""ERP AI TUI - Terminal User Interface"""

import sys
import os
import curses
import time
from datetime import datetime

# Import core modules
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine


# ANSI Colors (using ANSI escape sequences)
class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Backgrounds
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_PURPLE = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_PURPLE = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Theme (Catppuccin-inspired)
    THEME_BG = BG_BLACK
    THEME_FG = BRIGHT_WHITE
    THEME_USER = BRIGHT_BLUE
    THEME_AI = BRIGHT_GREEN
    THEME_BORDER = BRIGHT_BLACK
    THEME_ACCENT = BRIGHT_YELLOW
    THEME_ERROR = BRIGHT_RED
    THEME_INPUT = BRIGHT_PURPLE


def color_text(text, color):
    """Wrap text with ANSI color codes"""
    return f"{color}{text}{Colors.RESET}"


class TUIScreen:
    """Main TUI screen manager"""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.chat_width = int(self.width * 0.7)
        self.data_width = self.width - self.chat_width - 1
        
        # State
        self.messages = []
        self.input_text = ""
        self.command_mode = False
        self.running = True
        
    def draw_header(self):
        """Draw the header bar"""
        title = " ERP AI Assistant "
        hint = f"{Colors.THEME_ACCENT}[Ctrl+K: Command]{Colors.RESET}"
        
        y = 0
        self.stdscr.addstr(y, 0, title, curses.A.BOLD | curses.color_content(7))
        self.stdscr.addstr(y, self.width - len(hint) + 1, hint)
        
    def draw_divider(self):
        """Draw vertical divider between panels"""
        for y in range(1, self.height - 1):
            self.stdscr.addstr(y, self.chat_width, "│")
            
    def draw_chat_panel(self):
        """Draw chat panel (left side)"""
        # Draw messages
        display_start = max(0, len(self.messages) - (self.height - 5)
        
        for i, msg in enumerate(self.messages[display_start:]):
            y = i + 1 - display_start + len(self.messages) - display_start
            if y >= self.height - 2:
                break
                
            role, content = msg
            prefix = color_text(f"  {role}: ", Colors.THEME_USER if role == "You" else Colors.THEME_AI)
            self.stdscr.addstr(y, 0, prefix)
            
            # Wrap text to fit panel
            wrapped = []
            words = content.split()
            line = ""
            for word in words:
                test_line =line + " " + word if line else word
                if len(test_line) < self.chat_width - 4:
                    line = test_line
                else:
                    wrapped.append(line)
                    line = word
            if line:
                wrapped.append(line)
                
            for j, line in enumerate(wrapped[:3]):  # Max 3 lines per message
                if y + j < self.height - 2:
                    self.stdscr.addstr(y + j, 0, "  " + line[:self.chat_width - 4])
                    
    def draw_input(self):
        """Draw input area"""
        y = self.height - 2
        prompt = color_text("> ", Colors.THEME_INPUT)
        self.stdscr.addstr(y, 0, prompt)
        self.stdscr.addstr(y, 2, self.input_text[:self.chat_width - 4])
        
    def draw_data_panel(self):
        """Draw data panel (right side)"""
        x = self.chat_width + 1
        
        # Tab header
        self.stdscr.addstr(1, x, " Context ")
        self.stdscr.addstr(1, x + 10, " History ", curses.A.REVERSE)
        
    def handle_input(self, key):
        """Handle keyboard input"""
        if key == 27:  # Escape
            self.command_mode = False
        elif key in (curses.KEY_BACKSPACE, 127):
            self.input_text = self.input_text[:-1]
        elif key == 10:  # Enter
            if self.input_text:
                self.messages.append(("You", self.input_text))
                self.input_text = ""
                return True  # Message to process
        elif 32 <= key <= 126:
            self.input_text += chr(key)
            
        return False
        
    def run(self, stdscr):
        """Main TUI loop"""
        curses.curs_set(1)
        stdscr.clear()
        
        while self.running:
            self.height, self.width = stdscr.getmaxyx()
            self.chat_width = int(self.width * 0.7)
            
            stdscr.clear()
            
            self.draw_header()
            self.draw_divider()
            self.draw_chat_panel()
            self.draw_data_panel()
            self.draw_input()
            
            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key == 3:  # Ctrl+C
                break
            elif key == 11:  # Ctrl+K
                self.command_mode = True
                
            if self.handle_input(key):
                # Process message - yield to main loop
                return self.messages[-1][1]
                
        return None


def main(stdscr):
    """Main entry point"""
    # Initialize
    config, db = run_startup()
    
    # Check providers
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    if not ollama_ok and not llamacpp_ok:
        print("ERROR: No LLM providers available!")
        return 1
        
    # Initialize components
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    if ollama_ok:
        llm.set_provider('ollama')
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        
    session_id = conv.start_session()
    
    # Run TUI
    screen = TUIScreen(stdscr)
    
    while screen.running:
        user_input = screen.run(stdscr)
        
        if user_input:
            conv.add_message(session_id, 'user', user_input)
            context = conv.get_conversation_summary(session_id)
            result = op.process(user_input, {'context': context})
            screen.messages.append(("AI", result))
            conv.add_message(session_id, 'assistant', result)
            
    return 0


if __name__ == "__main__":
    curses.wrapper(main)
```

- [ ] **Step 2: Test Python curses import**

Run: `python3 -c "import curses; print('OK')"`
Expected: OK (or error if curses unavailable on Windows)

- [ ] **Step 3: Commit skeleton**

```bash
git add tui.py
git commit -m "feat: add TUI module skeleton with curses"
```

---

## Chunk 2: run.sh Integration

### Task 2: Add TUI Mode to run.sh

**Files:**
- Modify: `run.sh:129-143` (mode selection)

- [ ] **Step 1: Update run.sh mode selection**

In `run.sh`, find lines 129-143:

```bash
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
```

Replace with:

```bash
echo
echo "═══════════════════════════════════════"
echo "Select app mode:"
echo "  1. Web UI (browser)"
echo "  2. CLI (terminal)"
echo "  3. TUI (terminal - split panels)"
echo

while true; do
    read -p "Choice: " MODE_CHOICE
    case $MODE_CHOICE in
        1) APP="web"; break ;;
        2) APP="cli"; break ;;
        3) APP="tui"; break ;;
        *) echo "Invalid. Enter 1, 2, or 3" ;;
    esac
done
```

- [ ] **Step 2: Add TUI to app launcher section**

Find lines 160-168:

```bash
if [ "$APP" = "web" ]; then
    echo "Starting Web UI..."
    echo "🌐 Open: http://localhost:5000"
    setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /dev/null 2>&1 &
    sleep 3
else
    echo "Starting CLI..."
    .venv/bin/python main.py
fi
```

Replace with:

```bash
if [ "$APP" = "web" ]; then
    echo "Starting Web UI..."
    echo "🌐 Open: http://localhost:5000"
    setsid .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app' > /dev/null 2>&1 &
    sleep 3
elif [ "$APP" = "tui" ]; then
    echo "Starting TUI..."
    .venv/bin/python -c "import curses; import tui"
else
    echo "Starting CLI..."
    .venv/bin/python main.py
fi
```

Actually, the TUI command should use curses.wrapper:

```bash
elif [ "$APP" = "tui" ]; then
    echo "Starting TUI..."
    .venv/bin/python -c "
import curses
import tui
curses.wrapper(tui.main)
"
```

- [ ] **Step 3: Commit run.sh changes**

```bash
git add run.sh
git commit -m "feat: add TUI mode to run.sh"
```

---

## Chunk 3: Polish & Testing

### Task 3: Polish TUI

**Files:**
- Modify: `tui.py` (enhance features)

- [ ] **Step 1: Add command palette support**

Add command handling:

```python
COMMANDS = {
    '/customers': 'List customers',
    '/items': 'List inventory',
    '/invoice': 'Generate invoice',
    '/switch': 'Toggle provider',
    '/clear': 'Clear chat',
    '/help': 'Show commands',
    '/quit': 'Exit',
    '/model': 'Show model',
}

def handle_command(self, cmd):
    """Handle command palette commands"""
    if cmd == '/help':
        return "Commands: " + ", ".join(COMMANDS.keys())
    elif cmd == '/clear':
        self.messages = []
        return None
    elif cmd == '/quit' or cmd == '/exit':
        self.running = False
        return None
    # Add more handlers...
    return f"Running: {cmd}"
```

- [ ] **Step 2: Add scroll support**

```python
def handle_input(self, key):
    # ... existing code ...
    elif key == curses.KEY_UP and self.messages:
        self.scroll_offset = max(0, self.scroll_offset - 1)
    elif key == curses.KEY_DOWN:
        self.scroll_offset += 1
```

- [ ] **Step 3: Commit polish**

```bash
git add tui.py
git commit -m "feat: add command palette and scroll to TUI"
```

### Task 4: Test TUI

- [ ] **Step 1: Run TUI in terminal**

Run: `./run.sh` and select TUI mode (option 3)

- [ ] **Step 2: Verify layout**

- Split panels visible
- Colors display
- Input works
- Commands work

- [ ] **Step 3: Commit test results**

```bash
git commit -m "test: verify TUI works"
```

---

## Summary

**Files created:**
- `tui.py` - Main TUI module

**Files modified:**
- `run.sh` - Added TUI mode option

**Dependencies:**
- Python standard library (curses) - no new deps needed

**Test verification:**
- [ ] TUI starts from run.sh
- [ ] Split panels render
- [ ] Colors display
- [ ] Commands work
- [ ] Can process messages