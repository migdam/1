#!/usr/bin/env python3
"""Example: Advanced usage with custom settings and filtering."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    get_config,
    setup_logger,
    MetadataDB,
    TextExtractor,
    TextChunker,
    create_embedder,
    VectorDB,
    Retriever,
)


def example_1_process_single_book():
    """Example: Process a single book."""
    print("\n" + "=" * 60)
    print("Example 1: Process a Single Book")
    print("=" * 60)

    config = get_config()
    logger = setup_logger("example", console=True)

    # Initialize components
    extractor = TextExtractor(logger=logger)
    chunker = TextChunker(logger=logger)
    embedder = create_embedder(logger=logger)
    vector_db = VectorDB(dimension=embedder.embedding_dim, logger=logger)
    metadata_db = MetadataDB()

    # Process a book
    book_path = Path("books/example.pdf")  # Replace with your book

    if not book_path.exists():
        print(f"Book not found: {book_path}")
        return

    # Extract text
    print(f"Extracting text from {book_path.name}...")
    text, metadata = extractor.extract(book_path)

    if not text:
        print("Failed to extract text")
        return

    print(f"Extracted {len(text)} characters")

    # Chunk text
    print("Chunking text...")
    chunks = chunker.chunk_text(text, metadata)
    print(f"Created {len(chunks)} chunks")

    # Generate embeddings
    print("Generating embeddings...")
    embeddings = embedder.encode_chunks(chunks, show_progress=True)
    print(f"Generated {len(embeddings)} embeddings")

    # Add to vector DB
    print("Adding to vector database...")
    vector_metadata = [
        {
            'chunk_index': i,
            'book_title': metadata.get('title', book_path.stem),
            'chunk_text': chunk.text[:100]
        }
        for i, chunk in enumerate(chunks)
    ]
    vector_db.add(embeddings, vector_metadata)
    print(f"Vector database size: {vector_db.size()}")

    # Save
    vector_db.save("./data/example_index")
    print("Saved vector database")


def example_2_search_with_filters():
    """Example: Search with metadata filters."""
    print("\n" + "=" * 60)
    print("Example 2: Search with Metadata Filters")
    print("=" * 60)

    config = get_config()
    logger = setup_logger("example", console=True)

    # Load components
    embedder = create_embedder(logger=logger)
    vector_db = VectorDB.load("./data/books_index", logger=logger)
    metadata_db = MetadataDB()

    # Create retriever
    retriever = Retriever(
        embedder=embedder,
        vector_db=vector_db,
        metadata_db=metadata_db,
        top_k=10,
        logger=logger
    )

    # Search with filters
    query = "What is consciousness?"

    # Example: Only search in philosophy books
    filters = {
        'detected_language': 'en',  # Only English books
    }

    print(f"Query: {query}")
    print(f"Filters: {filters}")

    results = retriever.retrieve(query, filters=filters)

    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result.book_title}")
        print(f"    Score: {result.similarity_score:.4f}")
        print(f"    Text: {result.chunk_text[:150]}...")


def example_3_batch_processing():
    """Example: Batch process multiple queries."""
    print("\n" + "=" * 60)
    print("Example 3: Batch Query Processing")
    print("=" * 60)

    config = get_config()
    logger = setup_logger("example", console=True)

    # Load components
    from src import load_vector_db, create_llm_from_config, create_rag_pipeline

    metadata_db = MetadataDB()
    embedder = create_embedder(logger=logger)
    vector_db = load_vector_db(str(config.vector_db_path), logger=logger)
    llm_client = create_llm_from_config(config, logger=logger)

    rag_pipeline = create_rag_pipeline(
        embedder, vector_db, metadata_db, llm_client, config, logger
    )

    # Multiple queries
    questions = [
        "What is love?",
        "How do we find happiness?",
        "What is the purpose of life?",
    ]

    print(f"Processing {len(questions)} queries...\n")

    results = rag_pipeline.batch_query(questions)

    for question, (answer, sources) in zip(questions, results):
        print("=" * 60)
        print(f"Q: {question}")
        print("-" * 60)
        print(f"A: {answer[:200]}...")
        print(f"Sources: {len(sources)} documents")
        print()


def example_4_custom_prompt():
    """Example: Use custom RAG prompt."""
    print("\n" + "=" * 60)
    print("Example 4: Custom RAG Prompt")
    print("=" * 60)

    config = get_config()
    logger = setup_logger("example", console=True)

    # Load components
    from src import load_vector_db, create_llm_from_config, create_rag_pipeline

    metadata_db = MetadataDB()
    embedder = create_embedder(logger=logger)
    vector_db = load_vector_db(str(config.vector_db_path), logger=logger)
    llm_client = create_llm_from_config(config, logger=logger)

    rag_pipeline = create_rag_pipeline(
        embedder, vector_db, metadata_db, llm_client, config, logger
    )

    # Custom prompt template
    custom_prompt = """You are a philosophical advisor.

Based on the following book excerpts, provide a thoughtful and nuanced answer.
Cite your sources and acknowledge different viewpoints if they exist.

Book Excerpts:
{context}

Question:
{query}

Thoughtful Response:"""

    question = "What is wisdom?"

    print(f"Question: {question}")
    print("Using custom prompt template...\n")

    # Query with custom prompt
    results = rag_pipeline.retriever.retrieve(question)
    context = rag_pipeline.retriever.build_context(results)

    prompt = custom_prompt.format(context=context, query=question)
    answer = rag_pipeline.llm_client.generate(prompt)

    print("Answer:")
    print(answer)


def example_5_statistics():
    """Example: Get library statistics."""
    print("\n" + "=" * 60)
    print("Example 5: Library Statistics")
    print("=" * 60)

    metadata_db = MetadataDB()
    stats = metadata_db.get_stats()

    print("\nLibrary Statistics:")
    print(f"  Total books: {stats['total_books']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Total words: {stats['total_words']:,}")
    print(f"  Average extraction time: {stats['avg_extraction_time']:.2f}s")
    print(f"  Average embedding time: {stats['avg_embedding_time']:.2f}s")

    print("\nBooks by status:")
    for status, count in stats['books_by_status'].items():
        print(f"  {status}: {count}")

    print("\nBooks by format:")
    for fmt, count in stats['books_by_format'].items():
        print(f"  {fmt}: {count}")

    # List recent books
    print("\nRecent books:")
    books = metadata_db.list_books(limit=5)
    for book in books:
        print(f"  - {book['title']} ({book['chunk_count']} chunks)")


if __name__ == '__main__':
    print("AI Library - Advanced Examples")
    print("=" * 60)

    # Uncomment the examples you want to run:

    # example_1_process_single_book()
    # example_2_search_with_filters()
    # example_3_batch_processing()
    # example_4_custom_prompt()
    example_5_statistics()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
