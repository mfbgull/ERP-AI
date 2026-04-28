import sys
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine


def main():
    print("ERP AI Assistant starting...")
    
    config, db = run_startup()
    
    print("\n✓ System ready!")
    print(f"  Database: {config['database']['path']}")
    print("\nType your request or 'quit' to exit.")
    
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    if ollama_ok:
        llm.set_provider('ollama')
        print(f"  LLM: Ollama ({config['ollama']['model']})")
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        print("  LLM: llama.cpp")
    else:
        print("  LLM: None available")
    
    session_id = conv.start_session()
    print(f"  Session: {session_id[:8]}...\n")
    
    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            break
        
        if not user_input:
            continue
        if user_input.lower() in ('quit', 'exit'):
            break
        
        if user_input.startswith('/'):
            cmd = user_input[1:].lower().split()[0]
            
            if cmd == 'switch':
                new_provider = 'llama_cpp' if llm.current_provider == 'ollama' else 'ollama'
                msg = llm.switch_provider(new_provider)
                print(f"[AI] {msg}")
            elif cmd == 'customers':
                results = db.execute("SELECT * FROM customers LIMIT 10")
                print(format_results(results))
            elif cmd == 'items':
                results = db.execute("SELECT * FROM items LIMIT 10")
                print(format_results(results))
            elif cmd == 'help':
                print("Commands: /customers, /items, /switch")
            else:
                print(f"Unknown: {cmd}")
            continue
        
        conv.add_message(session_id, 'user', user_input)
        
        try:
            context = conv.get_conversation_summary(session_id)
            result = op.process(user_input, {'context': context})
            print(f"\n{result}\n")
            conv.add_message(session_id, 'assistant', result)
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")


def format_results(rows):
    if not rows:
        return "No results."
    if len(rows) == 1:
        return "\n".join(f"{k}: {v}" for k, v in rows[0].items())
    
    headers = list(rows[0].keys())
    header_line = " | ".join(headers)
    lines = [header_line, "-" * len(header_line)]
    for row in rows:
        lines.append(" | ".join(str(row.get(h, '')) for h in headers))
    return "\n".join(lines)


if __name__ == "__main__":
    main()