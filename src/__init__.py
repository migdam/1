"""AI Library & Knowledge Engine - Core modules."""

__version__ = "1.0.0"
__author__ = "AI Library Team"
__description__ = "Local-first RAG system for semantic search across book collections"

from .config_loader import Config, get_config
from .logger import setup_logger, get_global_logger
from .metadata_db import MetadataDB
from .text_extractor import TextExtractor
from .chunker import TextChunker, Chunk
from .embedder import Embedder, create_embedder
from .vector_db import VectorDB, create_vector_db, load_vector_db
from .llm_client import LLMClient, create_llm_client, create_llm_from_config
from .retriever import Retriever, RAGPipeline, create_rag_pipeline

__all__ = [
    'Config',
    'get_config',
    'setup_logger',
    'get_global_logger',
    'MetadataDB',
    'TextExtractor',
    'TextChunker',
    'Chunk',
    'Embedder',
    'create_embedder',
    'VectorDB',
    'create_vector_db',
    'load_vector_db',
    'LLMClient',
    'create_llm_client',
    'create_llm_from_config',
    'Retriever',
    'RAGPipeline',
    'create_rag_pipeline',
]
