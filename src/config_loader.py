"""Configuration loader for AI Library & Knowledge Engine."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """Configuration manager for the AI Library system."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file.

        Args:
            config_path: Path to the configuration YAML file
        """
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

        # Load environment variables
        load_dotenv()

    def load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        # Create necessary directories
        self._create_directories()

    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        paths = self._config.get('paths', {})
        for path_key, path_value in paths.items():
            if path_key != 'vector_db':  # Vector DB might be a file
                Path(path_value).mkdir(parents=True, exist_ok=True)

        # Create vector DB directory
        vector_db_path = Path(paths.get('vector_db', './data/books_index'))
        vector_db_path.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (e.g., 'llm.provider').

        Args:
            key: Dot-separated key path
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: str = None) -> None:
        """Save configuration to YAML file.

        Args:
            path: Optional path to save to (defaults to original path)
        """
        save_path = Path(path) if path else self.config_path

        with open(save_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self.get('embedding.model', 'intfloat/e5-small-v2')

    @property
    def embedding_batch_size(self) -> int:
        """Get embedding batch size."""
        return self.get('embedding.batch_size', 32)

    @property
    def embedding_device(self) -> str:
        """Get embedding device (cpu/cuda)."""
        return self.get('embedding.device', 'cpu')

    @property
    def llm_provider(self) -> str:
        """Get LLM provider."""
        return self.get('llm.provider', 'local')

    @property
    def top_k(self) -> int:
        """Get number of chunks to retrieve."""
        return self.get('rag.top_k', 5)

    @property
    def chunk_size(self) -> int:
        """Get chunk size in words."""
        return self.get('chunking.chunk_size', 1000)

    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap in words."""
        return self.get('chunking.chunk_overlap', 100)

    @property
    def books_path(self) -> Path:
        """Get books directory path."""
        return Path(self.get('paths.books', './books'))

    @property
    def text_output_path(self) -> Path:
        """Get text output directory path."""
        return Path(self.get('paths.text_output', './text_books'))

    @property
    def vector_db_path(self) -> Path:
        """Get vector database path."""
        return Path(self.get('paths.vector_db', './data/books_index'))

    @property
    def metadata_db_path(self) -> Path:
        """Get metadata database path."""
        return Path(self.get('paths.metadata_db', './data/books_metadata.db'))

    @property
    def logs_path(self) -> Path:
        """Get logs directory path."""
        return Path(self.get('paths.logs', './logs'))

    def get_llm_config(self, provider: str = None) -> Dict[str, Any]:
        """Get LLM configuration for a specific provider.

        Args:
            provider: LLM provider name (defaults to configured provider)

        Returns:
            LLM configuration dictionary
        """
        if provider is None:
            provider = self.llm_provider

        llm_config = self.get(f'llm.{provider}', {})

        # Add API key from environment if specified
        if 'api_key_env' in llm_config:
            api_key_env = llm_config['api_key_env']
            api_key = os.getenv(api_key_env)
            if api_key:
                llm_config['api_key'] = api_key

        return llm_config

    def get_supported_formats(self) -> list:
        """Get list of supported file formats."""
        return self.get('formats.supported', ['.pdf', '.epub', '.txt', '.docx'])

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config(path={self.config_path})"


# Global config instance
_config_instance = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get or create global configuration instance.

    Args:
        config_path: Path to configuration file

    Returns:
        Config instance
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = Config(config_path)

    return _config_instance


def reload_config(config_path: str = "config.yaml") -> Config:
    """Reload configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        New Config instance
    """
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
