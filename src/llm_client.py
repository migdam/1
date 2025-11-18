"""LLM client for multiple providers (OpenAI, Gemini, Claude, Ollama)."""

import os
import subprocess
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

# Import LLM libraries with error handling
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class BaseLLM(ABC):
    """Base class for LLM clients."""

    def __init__(self, logger=None):
        """Initialize base LLM client.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass


class OpenAIClient(BaseLLM):
    """OpenAI API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        logger=None
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name
            logger: Optional logger instance
        """
        super().__init__(logger)

        if not HAS_OPENAI:
            raise ImportError("openai library not installed")

        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

        self._log('info', f"Initialized OpenAI client with model: {model}")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using OpenAI API.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            self._log('error', f"OpenAI API error: {str(e)}")
            raise


class GeminiClient(BaseLLM):
    """Google Gemini API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        logger=None
    ):
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key
            model: Model name
            logger: Optional logger instance
        """
        super().__init__(logger)

        if not HAS_GEMINI:
            raise ImportError("google-generativeai library not installed")

        self.api_key = api_key
        self.model = model

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

        self._log('info', f"Initialized Gemini client with model: {model}")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Gemini API.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            generation_config = {
                'temperature': temperature,
                'max_output_tokens': max_tokens,
            }

            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            self._log('error', f"Gemini API error: {str(e)}")
            raise


class ClaudeClient(BaseLLM):
    """Anthropic Claude API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        logger=None
    ):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Model name
            logger: Optional logger instance
        """
        super().__init__(logger)

        if not HAS_ANTHROPIC:
            raise ImportError("anthropic library not installed")

        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

        self._log('info', f"Initialized Claude client with model: {model}")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Claude API.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            self._log('error', f"Claude API error: {str(e)}")
            raise


class OllamaClient(BaseLLM):
    """Ollama local LLM client."""

    def __init__(
        self,
        model: str = "gemma2:9b",
        host: str = "http://localhost:11434",
        logger=None
    ):
        """Initialize Ollama client.

        Args:
            model: Model name
            host: Ollama server host
            logger: Optional logger instance
        """
        super().__init__(logger)

        self.model = model
        self.host = host

        self._log('info', f"Initialized Ollama client with model: {model}")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text using Ollama.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate (not used, for compatibility)

        Returns:
            Generated text
        """
        try:
            # Use subprocess to call ollama
            cmd = [
                "ollama",
                "run",
                self.model,
                prompt
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            self._log('error', "Ollama request timed out")
            raise RuntimeError("Ollama request timed out")
        except FileNotFoundError:
            self._log('error', "Ollama not found. Is it installed?")
            raise RuntimeError("Ollama not found. Install from https://ollama.ai")
        except Exception as e:
            self._log('error', f"Ollama error: {str(e)}")
            raise


class LLMClient:
    """Unified LLM client that supports multiple providers."""

    def __init__(self, provider: str, config: Dict[str, Any], logger=None):
        """Initialize LLM client for a specific provider.

        Args:
            provider: Provider name (openai, gemini, claude, local)
            config: Provider configuration
            logger: Optional logger instance
        """
        self.provider = provider
        self.config = config
        self.logger = logger

        # Create appropriate client
        if provider == "openai":
            if 'api_key' not in config:
                raise ValueError("OpenAI API key not provided")
            self.client = OpenAIClient(
                api_key=config['api_key'],
                model=config.get('model', 'gpt-4o-mini'),
                logger=logger
            )

        elif provider == "gemini":
            if 'api_key' not in config:
                raise ValueError("Gemini API key not provided")
            self.client = GeminiClient(
                api_key=config['api_key'],
                model=config.get('model', 'gemini-2.0-flash-exp'),
                logger=logger
            )

        elif provider == "claude":
            if 'api_key' not in config:
                raise ValueError("Claude API key not provided")
            self.client = ClaudeClient(
                api_key=config['api_key'],
                model=config.get('model', 'claude-3-5-sonnet-20241022'),
                logger=logger
            )

        elif provider == "local":
            self.client = OllamaClient(
                model=config.get('model', 'gemma2:9b'),
                host=config.get('host', 'http://localhost:11434'),
                logger=logger
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            temperature: Optional sampling temperature (uses config default if not provided)
            max_tokens: Optional max tokens (uses config default if not provided)

        Returns:
            Generated text
        """
        if temperature is None:
            temperature = self.config.get('temperature', 0.7)

        if max_tokens is None:
            max_tokens = self.config.get('max_tokens', 2000)

        return self.client.generate(prompt, temperature, max_tokens)


def create_llm_client(
    provider: str,
    config: Dict[str, Any],
    logger=None
) -> LLMClient:
    """Create an LLM client for a specific provider.

    Args:
        provider: Provider name (openai, gemini, claude, local)
        config: Provider configuration
        logger: Optional logger instance

    Returns:
        LLMClient instance
    """
    return LLMClient(provider, config, logger)


def create_llm_from_config(config_obj, logger=None) -> LLMClient:
    """Create an LLM client from a configuration object.

    Args:
        config_obj: Configuration object with get_llm_config method
        logger: Optional logger instance

    Returns:
        LLMClient instance
    """
    provider = config_obj.llm_provider
    llm_config = config_obj.get_llm_config(provider)

    return create_llm_client(provider, llm_config, logger)
