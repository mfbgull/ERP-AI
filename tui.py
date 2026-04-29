#!/usr/bin/env python3
import curses
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine


COMMANDS = {
    '/help': 'Show commands',
    '/clear': 'Clear chat',
    '/quit': 'Exit',
    '/model': 'Show model',
}


class TUI:
    def __init__(self, stdscr, cfg, db, llm, op, conv, sid):
        self.s = stdscr
        self.cfg = cfg
        self.db = db
        self.llm = llm
        self.op = op
        self.conv = conv
        self.sid = sid
        self.msgs = []
        self.inp = ""
        self.cmd = False
        self.run = True
        
    def size(self):
        self.h, self.w = self.s.getmaxyx()
        self.cw = self.w - 22
        
    def draw(self):
        self.s.clear()
        self.size()
        h, w, cw = self.h, self.w, self.cw
        
        try:
            self.s.addstr(0, 0, " ERP AI [Ctrl+K]"[:w-1])
            self.s.addstr(1, 0, "-" * min(w, w))
            self.s.addstr(1, cw, "|")
            self.s.addstr(h-1, 0, "-" * min(w-1, w))
        except:
            pass
        
        start = max(0, len(self.msgs) - (h - 5))
        y = 2
        for role, txt in self.msgs[start:]:
            if y >= h - 2:
                break
            try:
                for line in txt.split('\n'):
                    if y >= h - 2:
                        break
                    self.s.addstr(y, 0, (f"{role}: " if y == 2 else "  ") + line[:cw-1])
                    y += 1
            except:
                pass
        
        p = "CMD> " if self.cmd else " > "
        try:
            self.s.addstr(h-2, 0, p + self.inp[:cw-len(p)-1])
            self.s.addstr(2, cw + 1, "[History]")
            self.s.addstr(4, cw + 1, f"Sess: {self.sid[:6]}")
            self.s.addstr(5, cw + 1, f"Model: {self.cfg.get('ollama',{}).get('model','?')[:10]}")
        except:
            pass
        
        self.s.refresh()
        
    def cmd_exec(self, c):
        c = c.strip().lower()
        if not c:
            self.cmd = False
            return None
        if c == '/help':
            return '\n'.join(f"{k}: {v}" for k,v in COMMANDS.items())
        if c == '/clear':
            self.msgs = []
            return "Cleared"
        if c in ('/quit','/exit'):
            self.run = False
            return "Bye"
        if c == '/model':
            return self.cfg.get('ollama',{}).get('model','N/A')
        return None
        
    def key(self, k):
        if self.cmd:
            if k in (10, 28):
                r = self.cmd_exec(self.inp)
                self.cmd = False
                if r:
                    self.msgs.append(("AI", r))
                self.inp = ""
                return None
            if k in (curses.KEY_BACKSPACE, 127, 8):
                self.inp = self.inp[:-1]
            elif k == 27:
                self.cmd = False
                self.inp = ""
            elif 32 <= k <= 126:
                self.inp += chr(k)
            return None
        
        if k in (curses.KEY_BACKSPACE, 127, 8):
            self.inp = self.inp[:-1]
        elif k == 10 and self.inp.strip():
            msg = self.inp
            self.inp = ""
            return msg
        elif k == 27:
            self.inp = ""
        elif 32 <= k <= 126:
            self.inp += chr(k)
        return None


def main(stdscr):
    try:
        curses.curs_set(1)
    except:
        pass
    
    cfg = load_config()
    db = Database(cfg['database']['path'])
    
    oll = check_ollama(cfg['ollama']['host'], cfg['ollama']['port'])
    llc = check_llama_cpp(cfg['llama_cpp']['host'], cfg['llama_cpp']['port'])
    
    if not oll and not llc:
        stdscr.addstr(0, 0, "ERROR: No LLM provider!")
        stdscr.refresh()
        return 1
    
    llm = LLMHandler(cfg)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    llm.set_provider('ollama' if oll else 'llama_cpp')
    sid = conv.start_session()
    
    t = TUI(stdscr, cfg, db, llm, op, conv, sid)
    
    while t.run:
        t.draw()
        k = t.s.getch()
        if k == 3:
            break
        if k == 11:
            t.cmd = True
        msg = t.key(k)
        if msg:
            t.msgs.append(("You", msg))
            try:
                ctx = conv.get_conversation_summary(sid)
                res = t.op.process(msg, {'context': ctx}, output_format='text')
            except Exception as e:
                res = f"Error: {e}"
            t.msgs.append(("AI", res))
            conv.add_message(sid, 'user', msg)
            conv.add_message(sid, 'assistant', res)


if __name__ == "__main__":
    s = curses.initscr()
    try:
        main(s)
    finally:
        curses.endwin()