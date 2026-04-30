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
    
    # Check if stdin is a TTY (interactive) or piped
    if not sys.stdin.isatty():
        # Non-interactive mode - just return current
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
    
    # Use enabled flags from config to determine provider preference
    ollama_enabled = config.get('ollama', {}).get('enabled', True)
    llamacpp_enabled = config.get('llama_cpp', {}).get('enabled', False)
    
    llm = LLMHandler(config)
    op = Operation(db, llm)
    conv = ConversationEngine(db)
    
    # Respect user's config choice, fall back to availability
    if ollama_enabled and ollama_ok:
        model = config['ollama']['model']
        models = get_ollama_models()
        if models:
            model = select_model(models, model)
            config['ollama']['model'] = model
        llm.set_provider('ollama')
        print(f"\n  Using Ollama: {model}")
    elif llamacpp_enabled and llamacpp_ok:
        llm.set_provider('llama_cpp')
        print("\n  Using: llama.cpp")
    elif ollama_ok:
        model = config['ollama']['model']
        models = get_ollama_models()
        if models:
            model = select_model(models, model)
            config['ollama']['model'] = model
        llm.set_provider('ollama')
        print(f"\n  Using Ollama: {model}")
    elif llamacpp_ok:
        llm.set_provider('llama_cpp')
        print("\n  Using: llama.cpp")
    
    session_id = conv.start_session()
    print(f"  Session: {session_id[:8]}...")
    print("\nType your request or 'quit' to exit.")
    print("Commands: /help, /clear, /model, /switch, /quit")
    
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return
        
        if not user_input:
            continue
        
        if user_input.lower() in ('quit', 'exit', '/quit', '/exit'):
            print("Goodbye!")
            return
        
        if user_input == '/help':
            print("\nCommands:")
            print("  /help     - Show this help")
            print("  /clear    - Clear chat history")
            print("  /model    - Show current model")
            print("  /switch   - Switch LLM provider")
            print("  /quit     - Exit")
            continue
        
        if user_input == '/clear':
            conv.sessions = {}
            session_id = conv.start_session()
            llm.clear_history()
            print("Chat history cleared.")
            continue
        
        if user_input == '/model':
            if llm.current_provider == 'ollama':
                models = get_ollama_models()
                current = config['ollama']['model']
                print(f"\nProvider: Ollama")
                print(f"Current: {current}")
                print(f"Available: {', '.join(models)}")
            else:
                print(f"\nProvider: llama.cpp")
            continue
        
        if user_input == '/switch':
            if ollama_ok and llamacpp_ok:
                new = 'llama_cpp' if llm.current_provider == 'ollama' else 'ollama'
                msg = llm.switch_provider(new)
                print(msg)
            else:
                print("Only one provider available.")
            continue
        
        # Process user message
        context = conv.get_context(session_id)
        conv.add_message(session_id, "user", user_input)
        
        try:
            result = op.process(user_input, {
                "context": conv.get_conversation_summary(session_id),
                "current_customer": context.get('current_customer_name'),
            })
            print(f"\n{result}\n")
            conv.add_message(session_id, "assistant", result)
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()