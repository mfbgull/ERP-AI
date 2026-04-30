"""Local Text-to-Speech (TTS) module for ERP AI Assistant.

Provides offline/on-device speech synthesis using speech-dispatcher (spd-say).
Designed for low-latency voice agent responses without external API dependencies.
"""

import os
import tempfile
import subprocess
import logging
import time
import json
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class LocalTTS:
    """Local Text-to-Speech engine using speech-dispatcher (spd-say)."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize local TTS engine.
        
        Args:
            config: Configuration dict with optional keys:
                - rate: Speech rate (-100 to +100, default 0)
                - pitch: Speech pitch (-100 to +100, default 0)
                - volume: Volume level (0 to 100, default 80)
                - voice: Voice variant (e.g., 'english', 'english_rp')
                - output_format: Not used (speech-dispatcher outputs directly)
        """
        self.config = config or {}
        self.rate = self.config.get('rate', 0)
        self.pitch = self.config.get('pitch', 0)
        self.volume = self.config.get('volume', 80)
        self.voice = self.config.get('voice', None)
        self.output_format = self.config.get('output_format', 'wav')
        self._initialized = False
        self._last_audio_duration = 0.0
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the TTS engine by checking spd-say availability."""
        try:
            result = subprocess.run(
                ['spd-say', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self._initialized = True
                logger.info("Local TTS engine initialized (speech-dispatcher)")
            else:
                logger.warning("speech-dispatcher not available")
        except FileNotFoundError:
            logger.warning("spd-say not found - TTS disabled")
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
    
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._initialized
    
    def synthesize(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Synthesize speech from text.
        
        Note: speech-dispatcher outputs audio directly to the system.
        This method returns metadata about the synthesis.
        
        Args:
            text: Text to synthesize
            output_path: Not used (kept for API compatibility)
        
        Returns:
            Dict with:
                - success: bool
                - text: str (synthesized text)
                - duration: float (estimated seconds)
                - audio_path: None (speech-dispatcher plays directly)
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'TTS engine not available',
                'audio_path': None,
                'duration': 0.0
            }
        
        if not text or not text.strip():
            return {
                'success': False,
                'error': 'Empty text',
                'audio_path': None,
                'duration': 0.0
            }
        
        # Clean text
        text = self._clean_text(text)
        
        start_time = time.time()
        
        try:
            # Build spd-say command
            cmd = ['spd-say', text]
            
            # Add rate
            cmd.extend(['-r', str(self.rate)])
            
            # Add pitch
            cmd.extend(['-p', str(self.pitch)])
            
            # Add volume
            cmd.extend(['-l', str(self.volume)])
            
            # Add voice if specified
            if self.voice:
                cmd.extend(['-t', self.voice])
            
            # Run synthesis (non-blocking, speech-dispatcher handles queuing)
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"spd-say failed: {error_msg}")
                return {
                    'success': False,
                    'error': f'spd-say error: {error_msg}',
                    'audio_path': None,
                    'duration': 0.0
                }
            
            # Estimate duration (rough estimate: ~150 words per minute at rate 0)
            words = len(text.split())
            base_wpm = 150
            rate_factor = 1.0 + (self.rate / 200)  # Rate adjustment
            estimated_duration = (words / base_wpm) * 60 / rate_factor
            self._last_audio_duration = estimated_duration
            
            generation_time = time.time() - start_time
            
            logger.info(f"Synthesized {len(text)} chars ({words} words) in {generation_time:.3f}s (est. duration: {estimated_duration:.2f}s)")
            
            return {
                'success': True,
                'text': text,
                'audio_path': None,  # speech-dispatcher plays directly
                'duration': estimated_duration,
                'generation_time': generation_time,
                'words': words,
                'rate': self.rate,
                'pitch': self.pitch,
                'volume': self.volume
            }
            
        except subprocess.TimeoutExpired:
            logger.error("TTS synthesis timed out")
            return {
                'success': False,
                'error': 'TTS synthesis timed out',
                'audio_path': None,
                'duration': 0.0
            }
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'audio_path': None,
                'duration': 0.0
            }
    
    def synthesize_to_bytes(self, text: str) -> Dict[str, Any]:
        """Synthesize speech and return result.
        
        Note: speech-dispatcher doesn't support direct audio capture.
        This returns the same result as synthesize().
        
        Args:
            text: Text to synthesize
        
        Returns:
            Dict with synthesis results
        """
        result = self.synthesize(text)
        result['note'] = 'speech-dispatcher plays audio directly to system'
        return result
    
    def speak(self, text: str, blocking: bool = True):
        """Speak text directly.
        
        Args:
            text: Text to speak
            blocking: If True, use --wait flag (not fully blocking with spd-say)
        """
        if not self.is_available():
            logger.warning("TTS not available")
            return
        
        text = self._clean_text(text)
        
        cmd = ['spd-say', text]
        cmd.extend(['-r', str(self.rate)])
        cmd.extend(['-p', str(self.pitch)])
        cmd.extend(['-l', str(self.volume)])
        
        if self.voice:
            cmd.extend(['-t', self.voice])
        
        if blocking:
            cmd.append('--wait')
        
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            logger.error(f"Failed to speak: {e}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for synthesis."""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Limit length
        if len(text) > 5000:
            text = text[:5000] + "..."
            logger.warning("Text truncated to 5000 characters")
        
        return text
    
    def get_voices(self) -> list:
        """Get available voices from speech-dispatcher.
        
        Returns:
            List of available voice variants
        """
        try:
            result = subprocess.run(
                ['spd-say', '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse help output for voice options
            voices = []
            for variant in ['english', 'english_rp', 'english_wm', 'english_us']:
                voices.append({
                    'id': variant,
                    'name': variant.replace('_', ' ').title(),
                    'languages': ['en'],
                    'gender': 'unknown'
                })
            
            return voices
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []
    
    def set_rate(self, rate: int):
        """Set speech rate (-100 to +100)."""
        self.rate = max(-100, min(100, rate))
    
    def set_pitch(self, pitch: int):
        """Set speech pitch (-100 to +100)."""
        self.pitch = max(-100, min(100, pitch))
    
    def set_volume(self, volume: int):
        """Set volume (0 to 100)."""
        self.volume = max(0, min(100, volume))
    
    def set_voice(self, voice_id: str):
        """Set voice variant."""
        self.voice = voice_id
    
    def stop(self):
        """Stop current speech."""
        try:
            subprocess.run(['spd-say', '--stop'], capture_output=True)
        except Exception as e:
            logger.error(f"Failed to stop speech: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self._initialized = False


class TTSManager:
    """Manager for TTS operations in voice agent context."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tts = LocalTTS(self.config.get('local_tts', {}))
        self.cache = {}  # Simple text-to-result cache
        self.cache_enabled = self.config.get('cache_enabled', True)
    
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self.tts.is_available()
    
    def synthesize(self, text: str, use_cache: bool = True) -> Dict[str, Any]:
        """Synthesize text to speech with optional caching.
        
        Args:
            text: Text to synthesize
            use_cache: Whether to use cached result if available
        
        Returns:
            Dict with synthesis results
        """
        # Check cache
        if use_cache and self.cache_enabled and text in self.cache:
            logger.info(f"Cache hit for text ({len(text)} chars)")
            cached = self.cache[text].copy()
            cached['cached'] = True
            return cached
        
        # Synthesize
        result = self.tts.synthesize(text)
        
        # Cache result
        if result['success'] and self.cache_enabled:
            self.cache[text] = result.copy()
            # Limit cache size
            if len(self.cache) > 100:
                # Remove oldest (first) item
                self.cache.pop(next(iter(self.cache)))
        
        result['cached'] = False
        return result
    
    def get_info(self) -> Dict[str, Any]:
        """Get TTS system information."""
        voices = self.tts.get_voices()
        
        return {
            'available': self.is_available(),
            'engine': 'speech-dispatcher (spd-say)',
            'type': 'local',
            'voices': voices,
            'current_voice': self.tts.voice or 'default',
            'rate': self.tts.rate,
            'pitch': self.tts.pitch,
            'volume': self.tts.volume,
            'cache_size': len(self.cache),
            'cache_enabled': self.cache_enabled,
            'latency_estimate_ms': 100,  # Very low latency for spd-say
            'note': 'Audio output through system audio (pulseaudio/ALSA)'
        }
    
    def clear_cache(self):
        """Clear result cache."""
        self.cache.clear()
        logger.info("TTS cache cleared")
    
    def cleanup(self):
        """Clean up all resources."""
        self.tts.cleanup()
        self.cache.clear()


# Global TTS manager instance
_tts_manager = None


def get_tts_manager(config: Dict[str, Any] = None) -> TTSManager:
    """Get or create global TTS manager instance.
    
    Args:
        config: Optional configuration
    
    Returns:
        TTSManager instance
    """
    global _tts_manager
    
    if _tts_manager is None:
        _tts_manager = TTSManager(config)
    
    return _tts_manager


def synthesize_text(text: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to synthesize text.
    
    Args:
        text: Text to synthesize
        config: Optional TTS configuration
    
    Returns:
        Synthesis result dict
    """
    manager = get_tts_manager(config)
    return manager.synthesize(text)


if __name__ == '__main__':
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    manager = get_tts_manager()
    info = manager.get_info()
    
    print("Local TTS System Info:")
    print(f"  Available: {info['available']}")
    print(f"  Engine: {info['engine']}")
    print(f"  Type: {info['type']}")
    print(f"  Voices: {len(info['voices'])}")
    for v in info['voices']:
        print(f"    - {v['name']} ({v['id']})")
    
    if info['available']:
        print("\nTesting synthesis...")
        result = manager.synthesize("Hello, this is a test of the local TTS system.")
        
        if result['success']:
            print(f"  ✓ Success!")
            print(f"  Text: {result['text']}")
            print(f"  Words: {result['words']}")
            print(f"  Est. Duration: {result['duration']:.2f}s")
            print(f"  Generation time: {result['generation_time']:.3f}s")
            print(f"  Cached: {result.get('cached', False)}")
        else:
            print(f"  ✗ Failed: {result['error']}")
    else:
        print("\n  TTS not available")

