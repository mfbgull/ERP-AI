import sys
from core.startup import run_startup, check_ollama, check_llama_cpp


def main():
    print("ERP AI Assistant starting...")
    
    config, db = run_startup()
    
    print("\n✓ System ready!")
    print(f"  Database: {config['database']['path']}")
    print("\nType your request or 'quit' to exit.")
    
    ollama_ok = check_ollama(config['ollama']['host'], config['ollama']['port'])
    llamacpp_ok = check_llama_cpp(config['llama_cpp']['host'], config['llama_cpp']['port'])
    
    if ollama_ok:
        print(f"  LLM: Ollama ({config['ollama']['model']})")
    elif llamacpp_ok:
        print("  LLM: llama.cpp")
    else:
        print("  LLM: None available")
    
    while True:
        user_input = input("\n> ")
        if user_input.lower() in ('quit', 'exit'):
            break
        print(f"[TODO] Processing: {user_input}")
    
    print("\nGoodbye!")


if __name__ == "__main__":
    main()