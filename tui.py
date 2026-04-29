#!/usr/bin/env python3
import sys
import os
import curses
import time
from datetime import datetime

from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_PURPLE = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    THEME_USER = BRIGHT_BLUE
    THEME_AI = BRIGHT_GREEN
    THEME_ACCENT = BRIGHT_YELLOW
    THEME_INPUT = BRIGHT_PURPLE
    THEME_TAB = BRIGHT_CYAN


def color(text, fg):
    return f"{fg}{text}{Colors.RESET}"


COMMANDS = {
    '/customers': 'List all customers',
    '/items': 'List inventory items',
    '/invoice': 'Generate invoice',
    '/switch': 'Toggle LLM provider',
    '/clear': 'Clear chat history',
    '/help': 'Show available commands',
    '/quit': 'Exit TUI',
    '/exit': 'Exit TUI',
    '/model': 'Show current model',
}


class TUIScreen:
    def __init__(self, stdscr, config, db, llm, op, conv, session_id):
        self.stdscr = stdscr
        self.config = config
        self.db = db
        self.llm = llm
        self.op = op
        self.conv = conv
        self.session_id = session_id
        
        self.height, self.width = stdscr.getmaxyx()
        self.chat_width = int(self.width * 0.7) - 1
        self.data_x = self.chat_width + 1
        
        self.messages = []
        self.input_text = ""
        self.command_mode = False
        self.running = True
        self.scroll_offset = 0
        self.active_tab = "history"
        
    def get_size(self):
        self.height, self.width = self.stdscr.getmaxyx()
        self.chat_width = int(self.width * 0.7) - 1
        self.data_x = self.chat_width + 1
        
    def draw_header(self):
        title = color(" ERP AI Assistant ", Colors.BOLD + Colors.BRIGHT_WHITE)
        hint = color("[Ctrl+K: Command]", Colors.THEME_ACCENT)
        
        self.stdscr.addstr(0, 0, title[:self.width-1])
        self.stdscr.addstr(0, self.width - len(hint) - 1, hint)
        
    def draw_border(self):
        self.stdscr.addstr(1, 0, "═" * (self.width))
        
        for y in range(2, self.height - 1):
            self.stdscr.addstr(y, self.chat_width, "│")
            
        self.stdscr.addstr(self.height - 1, 0, "═" * (self.width))
        
    def draw_chat(self):
        max_lines = self.height - 5
        start_idx = max(0, len(self.messages) - max_lines + self.scroll_offset)
        
        y = 2
        for i, msg in enumerate(self.messages[start_idx:]):
            if y >= self.height - 2:
                break
                
            role, content = msg
            prefix = color(f"  {role}: ", Colors.THEME_USER if role == "You" else Colors.THEME_AI)
            
            try:
                self.stdscr.addstr(y, 0, prefix)
            except curses.error:
                pass
            
            max_chars = self.chat_width - 4
            words = content.split()
            line = ""
            
            for word in words:
                test = (line + " " + word).strip() if line else word
                if len(test) <= max_chars:
                    line = test
                else:
                    if line:
                        try:
                            self.stdscr.addstr(y, 0, "  " + line)
                            y += 1
                            if y >= self.height - 2:
                                break
                        except curses.error:
                            pass
                    line = word
                    
            if line and y < self.height - 2:
                try:
                    self.stdscr.addstr(y, 0, "  " + line)
                except curses.error:
                    pass
                    
            y += 1
            
    def draw_input(self):
        y = self.height - 2
        if self.command_mode:
            prompt = color("CMD> ", Colors.THEME_ACCENT)
        else:
            prompt = color("  > ", Colors.THEME_INPUT)
            
        try:
            self.stdscr.addstr(y, 0, prompt)
            self.stdscr.addstr(y, len(prompt), self.input_text[:self.chat_width - len(prompt) - 2])
        except curses.error:
            pass
            
    def draw_data_panel(self):
        x = self.data_x + 1
        tab_y = 2
        
        hist_label = "  History  "
        if self.active_tab == "history":
            self.stdscr.addstr(tab_y, x, hist_label, curses.A_REVERSE)
        else:
            self.stdscr.addstr(tab_y, x, hist_label)
            
        ctx_label = "  Context "
        if self.active_tab == "context":
            self.stdscr.addstr(tab_y, x + 12, ctx_label, curses.A_REVERSE)
        else:
            self.stdscr.addstr(tab_y, x + 12, ctx_label)
            
        content_y = tab_y + 2
        
        if self.active_tab == "history":
            for i, msg in enumerate(self.messages[-5:]):
                if content_y + i >= self.height - 2:
                    break
                role, text = msg
                self.stdscr.addstr(content_y + i, x, f"{role}: "[:self.width - x - 2])
        else:
            self.stdscr.addstr(content_y, x, f"Session: {self.session_id[:8]}...")
            self.stdscr.addstr(content_y + 1, x, f"Model: {self.config.get('ollama', {}).get('model', 'N/A')}")
            self.stdscr.addstr(content_y + 2, x, f"Provider: {self.llm.current_provider}")
            
    def handle_command(self, cmd):
        cmd = cmd.strip().lower()
        
        if not cmd:
            self.command_mode = False
            return None
            
        if cmd == '/help':
            lines = ["Commands:"]
            for c, desc in COMMANDS.items():
                lines.append(f"  {c}: {desc}")
            return "\n".join(lines)
            
        elif cmd == '/clear':
            self.messages = []
            return "Chat cleared."
            
        elif cmd in ('/quit', '/exit'):
            self.running = False
            return "Goodbye!"
            
        elif cmd == '/switch':
            new = 'llama_cpp' if self.llm.current_provider == 'ollama' else 'ollama'
            try:
                self.llm.set_provider(new)
                return f"Switched to {new}"
            except Exception as e:
                return f"Error switching: {e}"
                
        elif cmd == '/model':
            return f"Current model: {self.config.get('ollama', {}).get('model', 'N/A')}"
            
        elif cmd in ('/customers', '/items'):
            return None
            
        else:
            return None
            
    def handle_input(self, key):
        if self.command_mode:
            if key in (10, 28):
                result = self.handle_command(self.input_text)
                self.command_mode = False
                if result:
                    self.messages.append(("AI", result))
                self.input_text = ""
                return None
            elif key in (curses.KEY_BACKSPACE, 127):
                self.input_text = self.input_text[:-1]
            elif key == 27:
                self.command_mode = False
                self.input_text = ""
            elif 32 <= key <= 126:
                self.input_text += chr(key)
            return None
            
        if key in (curses.KEY_BACKSPACE, 127):
            self.input_text = self.input_text[:-1]
        elif key == 10:
            if self.input_text.strip():
                msg = self.input_text
                self.input_text = ""
                return msg
        elif key == 27:
            self.input_text = ""
        elif key == curses.KEY_UP:
            self.scroll_offset = min(self.scroll_offset + 1, len(self.messages))
        elif key == curses.KEY_DOWN:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif 32 <= key <= 126:
            self.input_text += chr(key)
            
        return None
        
    def render(self):
        self.stdscr.clear()
        self.get_size()
        
        self.draw_header()
        self.draw_border()
        self.draw_chat()
        self.draw_input()
        self.draw_data_panel()
        
        self.stdscr.refresh()


def run_tui(stdscr, config, db, llm, op, conv, session_id):
    screen = TUIScreen(stdscr, config, db, llm, op, conv, session_id)
    
    while screen.running:
        screen.render()
        
        key = screen.stdscr.getch()
        
        if key == 3:
            break
        elif key == 11:
            screen.command_mode = True
            
        msg = screen.handle_input(key)
        
        if msg:
            screen.messages.append(("You", msg))
            
            try:
                context = conv.get_conversation_summary(session_id)
                result = op.process(msg, {'context': context})
            except Exception as e:
                result = f"Error: {e}"
                
            screen.messages.append(("AI", result))
            
            conv.add_message(session_id, 'user', msg)
            conv.add_message(session_id, 'assistant', result)


def main(stdscr):
    curses.curs_set(1)
    curses.echo()
    stdscr.nodelay(False)
    
    config, db = run_startup()
    
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    if not ollama_ok and not llamacpp_ok:
        print("ERROR: No LLM providers available!")
        return 1
        
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    if ollama_ok:
        llm.set_provider('ollama')
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        
    session_id = conv.start_session()
    
    run_tui(stdscr, config, db, llm, op, conv, session_id)
    
    return 0


if __name__ == "__main__":
    curses.wrapper(main)