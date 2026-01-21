"""
API Key Manager - Rotates through multiple API keys for load balancing
"""
import os
import threading


class APIKeyManager:
    """Thread-safe API key rotation manager"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Load keys from environment variable (comma-separated)
        keys_str = os.getenv("OPENAI_API_KEY", "")
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        if not self.keys:
            raise ValueError("No API keys found in OPENAI_API_KEY")
        
        self.usage = {key: 0 for key in self.keys}
        self.index = 0
        self._lock = threading.Lock()
        self._initialized = True
        print(f"[APIKeyManager] Initialized with {len(self.keys)} API keys")
    
    def get_next_key(self) -> str:
        """Get next API key in rotation (thread-safe)"""
        with self._lock:
            key = self.keys[self.index]
            self.usage[key] += 1
            self.index = (self.index + 1) % len(self.keys)
            # Log which key is being used (masked)
            masked = f"{key[:10]}...{key[-4:]}"
            print(f"[APIKeyManager] Using key: {masked} (usage: {self.usage[key]})")
            return key
    
    def get_key_usage(self) -> dict:
        """Get usage statistics for all keys"""
        return {f"{k[:10]}...{k[-4:]}": v for k, v in self.usage.items()}
    
    def get_key_count(self) -> int:
        """Get total number of keys"""
        return len(self.keys)


# Singleton instance
def get_api_key_manager() -> APIKeyManager:
    """Get the singleton APIKeyManager instance"""
    return APIKeyManager()