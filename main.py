import sys
import requests
from core.startup import run_startup, check_ollama, check_llama_cpp
from core.config import load_config
from core.database import Database
from core.llm_handler import LLMHandler
from core.operations import Operation
from core.conversation import ConversationEngine


def get_ollama_models():
    try:
        resp = requests.get('http://localhost:11434/api/tags', timeout=2)
        if resp.status_code == 200:
            return [m['name'] for m in resp.json().get('models', [])]
    except:
        pass
    return []


def select_model(models, current):
    if not models:
        return current
    
    print("\nAvailable models:")
    for i, m in enumerate(models, 1):
        marker = " (current)" if m == current else ""
        print(f"  {i}. {m}{marker}")
    
    while True:
        try:
            choice = input("\nSelect model (number) or press Enter to keep current: ").strip()
        except EOFError:
            return current
        
        if not choice:
            return current
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]
        except ValueError:
            pass


def main():
    print("ERP AI Assistant starting...")
    
    config, db = run_startup()
    
    print("\n✓ System ready!")
    print(f"  Database: {config['database']['path']}")
    
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    if not ollama_ok and not llamacpp_ok:
        print("  LLM: No providers available")
        return
    
    model = config['ollama']['model']
    if ollama_ok:
        models = get_ollama_models()
        if models:
            model = select_model(models, model)
            config['ollama']['model'] = model
    
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    if ollama_ok:
        llm.set_provider('ollama')
        print(f"\n  Using Ollama: {model}")
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        print("\n  Using: llama.cpp")
    
    session_id = conv.start_session()
    print(f"  Session: {session_id[:8]}...")
    print("\nType your request or 'quit' to exit.")
    
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
            elif cmd == 'model':
                models = get_ollama_models()
                if models:
                    print(f"\nAvailable: {', '.join(models)}")
                    print(f"Current: {config['ollama']['model']}")
            elif cmd == 'customers' or cmd == 'items':
                results = db.execute(f"SELECT * FROM {cmd} LIMIT 10")
                print(format_results(results))
            elif cmd == 'help':
                print("Commands: /customers, /items, /model, /switch, /quit")
            else:
                print(f"Unknown: {cmd}")
            continue
        
        conv.add_message(session_id, 'user', user_input)
        
        try:
            context = conv.get_conversation_summary(session_id)
            result = op.process(user_input, {'context': context}, output_format='text')
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