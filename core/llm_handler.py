import requests


class LLMHandler:
    def __init__(self, config: dict):
        self.config = config
        self.current_provider = None
        self.current_model = None
    
    def chat(self, prompt: str, system_prompt: str = "") -> str:
        if self.current_provider == 'ollama':
            return self._call_ollama(prompt, system_prompt)
        elif self.current_provider == 'llama_cpp':
            return self._call_llama_cpp(prompt, system_prompt)
        else:
            raise ValueError("No provider selected")
    
    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        cfg = self.config.get('ollama', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 11434)
        model = cfg.get('model', 'mistral')
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
        
        response = requests.post(
            f"http://{host}:{port}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")
        
        return response.json().get("response", "")
    
    def _call_llama_cpp(self, prompt: str, system_prompt: str) -> str:
        cfg = self.config.get('llama_cpp', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 8000)
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
        
        response = requests.post(
            f"http://{host}:{port}/completion",
            json={
                "prompt": full_prompt,
                "n_predict": 500,
                "temperature": 0.7
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"llama.cpp error: {response.text}")
        
        return response.json().get("content", "")
    
    def set_provider(self, provider: str):
        if provider not in ('ollama', 'llama_cpp'):
            raise ValueError(f"Unknown provider: {provider}")
        self.current_provider = provider
    
    def switch_provider(self, new_provider: str, conversation_history: list = None) -> str:
        old_provider = self.current_provider
        self.set_provider(new_provider)
        
        if old_provider:
            return f"Switched from {old_provider} to {new_provider}. Context transferred."
        return f"Switched to {new_provider}."