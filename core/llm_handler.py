import requests
import json
from typing import Optional, List, Dict, Generator


class LLMHandler:
    def __init__(self, config: dict):
        self.config = config
        self.current_provider = None
        self.current_model = None
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 20
        self.context_window = 4000  # tokens
    
    def chat(self, prompt: str, system_prompt: str = "", stream: bool = False) -> str:
        """Chat with optional streaming support."""
        if self.current_provider == 'ollama':
            return self._call_ollama(prompt, system_prompt, stream)
        elif self.current_provider == 'llama_cpp':
            return self._call_llama_cpp(prompt, system_prompt, stream)
        else:
            raise ValueError("No provider selected")
    
    def chat_stream(self, prompt: str, system_prompt: str = "") -> Generator[str, None, None]:
        """Stream chat responses."""
        if self.current_provider == 'ollama':
            yield from self._call_ollama_stream(prompt, system_prompt)
        else:
            # Fallback to non-streaming for llama.cpp
            yield self._call_llama_cpp(prompt, system_prompt)
    
    def _call_ollama(self, prompt: str, system_prompt: str, stream: bool = False) -> str:
        cfg = self.config.get('ollama', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 11434)
        model = cfg.get('model', 'mistral')
        
        full_prompt = self._build_prompt(prompt, system_prompt)
        
        try:
            response = requests.post(
                f"http://{host}:{port}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": stream,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500,
                        "top_p": 0.9,
                    }
                },
                timeout=cfg.get('timeout', 120)
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")
            
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.Timeout:
            raise RuntimeError("Ollama request timed out")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Ollama")
    
    def _call_ollama_stream(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        """Stream response from Ollama."""
        cfg = self.config.get('ollama', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 11434)
        model = cfg.get('model', 'mistral')
        
        full_prompt = self._build_prompt(prompt, system_prompt)
        
        try:
            response = requests.post(
                f"http://{host}:{port}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500,
                    }
                },
                timeout=cfg.get('timeout', 120),
                stream=True
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data.get("response", "")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise RuntimeError(f"Streaming error: {e}")
    
    def _call_llama_cpp(self, prompt: str, system_prompt: str, stream: bool = False) -> str:
        cfg = self.config.get('llama_cpp', {})
        host = cfg.get('host', 'localhost')
        port = cfg.get('port', 8000)
        
        full_prompt = self._build_prompt(prompt, system_prompt)
        
        try:
            response = requests.post(
                f"http://{host}:{port}/completion",
                json={
                    "prompt": full_prompt,
                    "n_predict": 500,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "stream": stream
                },
                timeout=120
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"llama.cpp error: {response.text}")
            
            return response.json().get("content", "")
        except requests.exceptions.Timeout:
            raise RuntimeError("llama.cpp request timed out")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to llama.cpp")
    
    def _build_prompt(self, prompt: str, system_prompt: str) -> str:
        """Build prompt with conversation history."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in self.conversation_history[-self.max_history:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": prompt})
        
        # Format for Ollama/llama.cpp
        if self.current_provider == 'ollama':
            # Use chat format if supported
            return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
        else:
            return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        # Trim history if too long
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def set_provider(self, provider: str):
        if provider not in ('ollama', 'llama_cpp'):
            raise ValueError(f"Unknown provider: {provider}")
        self.current_provider = provider
        self.clear_history()
    
    def switch_provider(self, new_provider: str, conversation_history: list = None) -> str:
        old_provider = self.current_provider
        self.set_provider(new_provider)
        
        if old_provider:
            if conversation_history:
                self.conversation_history = conversation_history
            return f"Switched from {old_provider} to {new_provider}. Context transferred."
        return f"Switched to {new_provider}."
    
    def get_context_size(self) -> int:
        """Estimate current context size in tokens."""
        # Rough estimate: 1 token ≈ 4 characters
        total_chars = sum(len(msg['content']) for msg in self.conversation_history)
        return total_chars // 4