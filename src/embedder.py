"""Embedding generation using local transformer models."""

import numpy as np
from pathlib import Path
from typing import List, Union, Optional
from tqdm import tqdm

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class Embedder:
    """Generate embeddings using SentenceTransformers."""

    def __init__(
        self,
        model_name: str = "intfloat/e5-small-v2",
        device: str = "cpu",
        batch_size: int = 32,
        cache_dir: Optional[str] = None,
        logger=None
    ):
        """Initialize embedder with a transformer model.

        Args:
            model_name: HuggingFace model name
            device: Device to use (cpu or cuda)
            batch_size: Batch size for encoding
            cache_dir: Directory to cache model files
            logger: Optional logger instance
        """
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.logger = logger

        self._log('info', f"Loading embedding model: {model_name}")

        # Create cache directory if specified
        if cache_dir:
            Path(cache_dir).mkdir(parents=True, exist_ok=True)

        # Load model
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_dir
            )
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self._log('info', f"Model loaded. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            self._log('error', f"Error loading model: {str(e)}")
            raise

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def encode(
        self,
        texts: Union[str, List[str]],
        show_progress: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """Encode texts into embeddings.

        Args:
            texts: Single text or list of texts
            show_progress: Show progress bar
            normalize: Normalize embeddings to unit length

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        self._log('debug', f"Encoding {len(texts)} texts")

        try:
            # Encode in batches
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )

            return embeddings

        except Exception as e:
            self._log('error', f"Error encoding texts: {str(e)}")
            raise

    def encode_batch(
        self,
        texts: List[str],
        show_progress: bool = True,
        normalize: bool = True
    ) -> np.ndarray:
        """Encode a batch of texts with progress tracking.

        Args:
            texts: List of texts to encode
            show_progress: Show progress bar
            normalize: Normalize embeddings

        Returns:
            Numpy array of embeddings
        """
        return self.encode(texts, show_progress=show_progress, normalize=normalize)

    def encode_chunks(
        self,
        chunks: List,
        show_progress: bool = True,
        normalize: bool = True
    ) -> np.ndarray:
        """Encode a list of Chunk objects.

        Args:
            chunks: List of Chunk objects with .text attribute
            show_progress: Show progress bar
            normalize: Normalize embeddings

        Returns:
            Numpy array of embeddings
        """
        texts = [chunk.text for chunk in chunks]
        return self.encode(texts, show_progress=show_progress, normalize=normalize)

    def get_embedding_dim(self) -> int:
        """Get embedding dimensionality.

        Returns:
            Embedding dimension
        """
        return self.embedding_dim

    def similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """Compute similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding
            metric: Similarity metric (cosine or dot)

        Returns:
            Similarity score
        """
        if metric == "cosine":
            # Assuming embeddings are already normalized
            return float(np.dot(embedding1, embedding2))
        elif metric == "dot":
            return float(np.dot(embedding1, embedding2))
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def __repr__(self) -> str:
        """String representation."""
        return f"Embedder(model={self.model_name}, dim={self.embedding_dim}, device={self.device})"


class CachedEmbedder:
    """Embedder with disk caching for computed embeddings."""

    def __init__(
        self,
        embedder: Embedder,
        cache_dir: str = "./cache/embeddings",
        logger=None
    ):
        """Initialize cached embedder.

        Args:
            embedder: Base Embedder instance
            cache_dir: Directory to cache embeddings
            logger: Optional logger instance
        """
        self.embedder = embedder
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def _get_cache_path(self, text_hash: str) -> Path:
        """Get cache file path for a text hash.

        Args:
            text_hash: Hash of the text

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{text_hash}.npy"

    def encode(
        self,
        texts: Union[str, List[str]],
        text_hashes: Optional[List[str]] = None,
        show_progress: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """Encode texts with caching.

        Args:
            texts: Single text or list of texts
            text_hashes: Optional list of pre-computed hashes
            show_progress: Show progress bar
            normalize: Normalize embeddings

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.array([])

        # Check cache
        embeddings = []
        texts_to_encode = []
        indices_to_encode = []

        for i, text in enumerate(texts):
            if text_hashes and i < len(text_hashes):
                cache_path = self._get_cache_path(text_hashes[i])
                if cache_path.exists():
                    try:
                        embedding = np.load(cache_path)
                        embeddings.append(embedding)
                        continue
                    except Exception:
                        pass

            # Need to encode this text
            embeddings.append(None)
            texts_to_encode.append(text)
            indices_to_encode.append(i)

        # Encode missing embeddings
        if texts_to_encode:
            self._log('debug', f"Encoding {len(texts_to_encode)} texts (cache miss)")
            new_embeddings = self.embedder.encode(
                texts_to_encode,
                show_progress=show_progress,
                normalize=normalize
            )

            # Update embeddings list and save to cache
            for idx, embedding in zip(indices_to_encode, new_embeddings):
                embeddings[idx] = embedding

                if text_hashes and idx < len(text_hashes):
                    cache_path = self._get_cache_path(text_hashes[idx])
                    try:
                        np.save(cache_path, embedding)
                    except Exception:
                        pass

        return np.array(embeddings)


def create_embedder(
    model_name: str = "intfloat/e5-small-v2",
    device: str = "cpu",
    batch_size: int = 32,
    cache_dir: Optional[str] = None,
    use_cache: bool = False,
    logger=None
) -> Union[Embedder, CachedEmbedder]:
    """Create an embedder instance.

    Args:
        model_name: HuggingFace model name
        device: Device to use (cpu or cuda)
        batch_size: Batch size for encoding
        cache_dir: Directory to cache model files
        use_cache: Whether to use embedding caching
        logger: Optional logger instance

    Returns:
        Embedder or CachedEmbedder instance
    """
    embedder = Embedder(
        model_name=model_name,
        device=device,
        batch_size=batch_size,
        cache_dir=cache_dir,
        logger=logger
    )

    if use_cache:
        return CachedEmbedder(
            embedder=embedder,
            cache_dir=cache_dir or "./cache/embeddings",
            logger=logger
        )

    return embedder
