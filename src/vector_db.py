"""Vector database for semantic search using FAISS."""

import pickle
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


class VectorDB:
    """FAISS-based vector database for semantic search."""

    def __init__(
        self,
        dimension: int,
        index_type: str = "IndexFlatIP",
        normalize: bool = True,
        logger=None
    ):
        """Initialize vector database.

        Args:
            dimension: Embedding dimension
            index_type: FAISS index type (IndexFlatIP, IndexFlatL2, IndexIVFFlat)
            normalize: Normalize vectors for cosine similarity
            logger: Optional logger instance
        """
        if not HAS_FAISS:
            raise ImportError(
                "faiss-cpu is not installed. "
                "Install it with: pip install faiss-cpu"
            )

        self.dimension = dimension
        self.index_type = index_type
        self.normalize = normalize
        self.logger = logger

        # Create FAISS index
        if index_type == "IndexFlatIP":
            # Inner product (use with normalized vectors for cosine similarity)
            self.index = faiss.IndexFlatIP(dimension)
        elif index_type == "IndexFlatL2":
            # L2 distance
            self.index = faiss.IndexFlatL2(dimension)
        elif index_type == "IndexIVFFlat":
            # IVF index for larger datasets (requires training)
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
        else:
            raise ValueError(f"Unknown index type: {index_type}")

        # Store metadata separately (FAISS doesn't store metadata)
        self.metadata: List[Dict[str, Any]] = []

        self._log('info', f"Initialized {index_type} with dimension {dimension}")

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def add(
        self,
        embeddings: np.ndarray,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Add embeddings to the index.

        Args:
            embeddings: Numpy array of embeddings (N x dimension)
            metadata: Optional list of metadata dictionaries
        """
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} "
                f"doesn't match index dimension {self.dimension}"
            )

        # Normalize if required
        if self.normalize:
            embeddings = self._normalize_vectors(embeddings)

        # Train index if needed (for IVF indices)
        if self.index_type == "IndexIVFFlat" and not self.index.is_trained:
            self._log('info', "Training IVF index...")
            self.index.train(embeddings)

        # Add to index
        self.index.add(embeddings.astype(np.float32))

        # Store metadata
        if metadata:
            if len(metadata) != len(embeddings):
                raise ValueError("Number of metadata entries must match number of embeddings")
            self.metadata.extend(metadata)
        else:
            # Add empty metadata
            self.metadata.extend([{}] * len(embeddings))

        self._log('debug', f"Added {len(embeddings)} embeddings to index")

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        return_metadata: bool = True
    ) -> List[Tuple[int, float, Optional[Dict[str, Any]]]]:
        """Search for similar vectors.

        Args:
            query_embedding: Query embedding
            k: Number of results to return
            return_metadata: Whether to return metadata

        Returns:
            List of (index, similarity_score, metadata) tuples
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        if query_embedding.shape[1] != self.dimension:
            raise ValueError(
                f"Query embedding dimension {query_embedding.shape[1]} "
                f"doesn't match index dimension {self.dimension}"
            )

        # Normalize if required
        if self.normalize:
            query_embedding = self._normalize_vectors(query_embedding)

        # Search
        k = min(k, self.index.ntotal)  # Don't request more than available
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)

        # Format results
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS returns -1 for missing results
                continue

            metadata = self.metadata[idx] if return_metadata and idx < len(self.metadata) else None
            results.append((int(idx), float(dist), metadata))

        return results

    def batch_search(
        self,
        query_embeddings: np.ndarray,
        k: int = 5,
        return_metadata: bool = True
    ) -> List[List[Tuple[int, float, Optional[Dict[str, Any]]]]]:
        """Search for similar vectors in batch.

        Args:
            query_embeddings: Query embeddings (N x dimension)
            k: Number of results per query
            return_metadata: Whether to return metadata

        Returns:
            List of result lists
        """
        if query_embeddings.ndim == 1:
            query_embeddings = query_embeddings.reshape(1, -1)

        # Normalize if required
        if self.normalize:
            query_embeddings = self._normalize_vectors(query_embeddings)

        # Search
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(query_embeddings.astype(np.float32), k)

        # Format results
        all_results = []
        for query_indices, query_distances in zip(indices, distances):
            results = []
            for idx, dist in zip(query_indices, query_distances):
                if idx == -1:
                    continue

                metadata = self.metadata[idx] if return_metadata and idx < len(self.metadata) else None
                results.append((int(idx), float(dist), metadata))

            all_results.append(results)

        return all_results

    @staticmethod
    def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors to unit length.

        Args:
            vectors: Numpy array of vectors

        Returns:
            Normalized vectors
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        return vectors / norms

    def save(self, path: str) -> None:
        """Save index and metadata to disk.

        Args:
            path: Path to save (without extension)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = str(path) + ".index"
        faiss.write_index(self.index, index_path)

        # Save metadata and config
        metadata_path = str(path) + ".meta"
        metadata_dict = {
            'metadata': self.metadata,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'normalize': self.normalize,
            'total_vectors': self.index.ntotal
        }

        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata_dict, f)

        self._log('info', f"Saved vector database to {path}")

    @classmethod
    def load(cls, path: str, logger=None) -> 'VectorDB':
        """Load index and metadata from disk.

        Args:
            path: Path to load from (without extension)
            logger: Optional logger instance

        Returns:
            VectorDB instance
        """
        if not HAS_FAISS:
            raise ImportError("faiss-cpu is not installed")

        path = Path(path)

        # Load FAISS index
        index_path = str(path) + ".index"
        if not Path(index_path).exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        index = faiss.read_index(index_path)

        # Load metadata
        metadata_path = str(path) + ".meta"
        if Path(metadata_path).exists():
            with open(metadata_path, 'rb') as f:
                metadata_dict = pickle.load(f)
        else:
            metadata_dict = {
                'metadata': [],
                'dimension': index.d,
                'index_type': 'IndexFlatIP',
                'normalize': True,
                'total_vectors': index.ntotal
            }

        # Create instance
        db = cls(
            dimension=metadata_dict['dimension'],
            index_type=metadata_dict['index_type'],
            normalize=metadata_dict['normalize'],
            logger=logger
        )

        # Replace index and metadata
        db.index = index
        db.metadata = metadata_dict['metadata']

        if logger:
            logger.info(
                f"Loaded vector database from {path} "
                f"({metadata_dict['total_vectors']} vectors)"
            )

        return db

    def size(self) -> int:
        """Get number of vectors in the index.

        Returns:
            Number of vectors
        """
        return self.index.ntotal

    def get_metadata(self, index: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific index.

        Args:
            index: Vector index

        Returns:
            Metadata dictionary or None
        """
        if 0 <= index < len(self.metadata):
            return self.metadata[index]
        return None

    def update_metadata(self, index: int, metadata: Dict[str, Any]) -> None:
        """Update metadata for a specific index.

        Args:
            index: Vector index
            metadata: New metadata
        """
        if 0 <= index < len(self.metadata):
            self.metadata[index] = metadata
        else:
            raise IndexError(f"Index {index} out of range")

    def clear(self) -> None:
        """Clear all vectors and metadata."""
        self.index.reset()
        self.metadata = []
        self._log('info', "Cleared vector database")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"VectorDB(type={self.index_type}, dim={self.dimension}, "
            f"size={self.size()}, normalize={self.normalize})"
        )


def create_vector_db(
    dimension: int,
    index_type: str = "IndexFlatIP",
    normalize: bool = True,
    logger=None
) -> VectorDB:
    """Create a new vector database.

    Args:
        dimension: Embedding dimension
        index_type: FAISS index type
        normalize: Normalize vectors for cosine similarity
        logger: Optional logger instance

    Returns:
        VectorDB instance
    """
    return VectorDB(
        dimension=dimension,
        index_type=index_type,
        normalize=normalize,
        logger=logger
    )


def load_vector_db(path: str, logger=None) -> VectorDB:
    """Load a vector database from disk.

    Args:
        path: Path to load from
        logger: Optional logger instance

    Returns:
        VectorDB instance
    """
    return VectorDB.load(path, logger=logger)
