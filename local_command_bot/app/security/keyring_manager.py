"""Secure API Key Management via Windows Credential Manager / Keyring."""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "LocalCommandBot"

# Supported Providers
SUPPORTED_PROVIDERS = ["openai", "anthropic", "gemini", "groq", "openrouter", "deepseek", "ollama", "custom"]

ENV_VAR_MAPPING = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    "custom": "CUSTOM_GATEWAY_KEY",
}


class KeyringManager:
    """Manages secure retrieval and storage of API keys."""

    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name
        self._memory_cache: dict[str, str] = {}

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key with fallback order:
        1. In-memory cache
        2. Environment variable
        3. OS Keyring (Windows Credential Manager)
        """
        provider_clean = provider.strip().lower()
        
        # 1. Check memory cache
        if provider_clean in self._memory_cache and self._memory_cache[provider_clean]:
            return self._memory_cache[provider_clean]

        # 2. Check environment variable
        env_var = ENV_VAR_MAPPING.get(provider_clean)
        if env_var:
            env_val = os.getenv(env_var)
            if env_val and env_val.strip():
                return env_val.strip()

        # 3. Check keyring
        try:
            import keyring
            val = keyring.get_password(self.service_name, provider_clean)
            if val and val.strip():
                self._memory_cache[provider_clean] = val.strip()
                return val.strip()
        except Exception as e:
            logger.warning(f"Could not read from keyring for provider '{provider}': {e}")

        return None

    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Store API key into OS Keyring and memory cache."""
        provider_clean = provider.strip().lower()
        key_clean = api_key.strip()
        
        self._memory_cache[provider_clean] = key_clean
        
        try:
            import keyring
            keyring.set_password(self.service_name, provider_clean, key_clean)
            return True
        except Exception as e:
            logger.warning(f"Failed to persist API key into keyring for provider '{provider}': {e}")
            return False

    def delete_api_key(self, provider: str) -> bool:
        """Remove API key from OS Keyring and memory cache."""
        provider_clean = provider.strip().lower()
        self._memory_cache.pop(provider_clean, None)
        
        try:
            import keyring
            keyring.delete_password(self.service_name, provider_clean)
            return True
        except Exception as e:
            logger.debug(f"Keyring delete notice for provider '{provider}': {e}")
            return False

    def has_api_key(self, provider: str) -> bool:
        """Check if an API key exists for a provider."""
        key = self.get_api_key(provider)
        return bool(key and len(key.strip()) > 0)


# Global instance
secret_manager = KeyringManager()
