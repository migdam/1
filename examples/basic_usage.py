#!/usr/bin/env python3
"""Example: Basic usage of the AI Library system."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    get_config,
    setup_logger,
    MetadataDB,
    create_embedder,
    load_vector_db,
    create_llm_from_config,
    create_rag_pipeline
)


def main():
    """Basic usage example."""

    # 1. Load configuration
    print("Loading configuration...")
    config = get_config("config.yaml")

    # 2. Setup logger
    logger = setup_logger("example", console=True)
    logger.info("Starting AI Library example")

    # 3. Load metadata database
    print("Loading metadata database...")
    metadata_db = MetadataDB(str(config.metadata_db_path))
    stats = metadata_db.get_stats()
    print(f"  - Total books: {stats['total_books']}")
    print(f"  - Total chunks: {stats['total_chunks']}")

    # 4. Load embedder
    print("Loading embedding model...")
    embedder = create_embedder(
        model_name=config.embedding_model,
        device=config.embedding_device,
        logger=logger
    )
    print(f"  - Model: {embedder.model_name}")
    print(f"  - Dimension: {embedder.embedding_dim}")

    # 5. Load vector database
    print("Loading vector database...")
    vector_db = load_vector_db(str(config.vector_db_path), logger=logger)
    print(f"  - Size: {vector_db.size()} vectors")

    # 6. Create LLM client
    print("Creating LLM client...")
    llm_client = create_llm_from_config(config, logger=logger)
    print(f"  - Provider: {config.llm_provider}")

    # 7. Create RAG pipeline
    print("Creating RAG pipeline...")
    rag_pipeline = create_rag_pipeline(
        embedder=embedder,
        vector_db=vector_db,
        metadata_db=metadata_db,
        llm_client=llm_client,
        config=config,
        logger=logger
    )

    # 8. Query the system
    print("\n" + "=" * 60)
    print("Ready! Let's ask a question...")
    print("=" * 60)

    question = "What is the meaning of life?"
    print(f"\nQuestion: {question}")
    print("\nSearching...")

    answer, results = rag_pipeline.query(question)

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(answer)

    print("\n" + "=" * 60)
    print("SOURCES")
    print("=" * 60)
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result.book_title} by {result.book_author}")
        print(f"    Score: {result.similarity_score:.4f}")
        print(f"    Preview: {result.chunk_text[:200]}...")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
