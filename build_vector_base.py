#!/usr/bin/env python3
"""Build vector database from book collection."""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_loader import get_config
from logger import init_global_logger, get_global_logger, PerformanceLogger
from metadata_db import MetadataDB
from text_extractor import TextExtractor
from chunker import TextChunker
from embedder import create_embedder
from vector_db import VectorDB


def process_book(
    file_path: Path,
    extractor: TextExtractor,
    chunker: TextChunker,
    embedder,
    vector_db: VectorDB,
    metadata_db: MetadataDB,
    config,
    logger
) -> bool:
    """Process a single book.

    Args:
        file_path: Path to book file
        extractor: TextExtractor instance
        chunker: TextChunker instance
        embedder: Embedder instance
        vector_db: VectorDB instance
        metadata_db: MetadataDB instance
        config: Configuration object
        logger: Logger instance

    Returns:
        True if successful
    """
    perf = PerformanceLogger(logger)
    perf.start("process_book")

    try:
        # Check if already processed
        existing_book = metadata_db.get_book_by_path(str(file_path))
        if existing_book and config.get('processing.skip_existing', True):
            if existing_book['status'] == 'completed':
                logger.info(f"Skipping already processed book: {file_path.name}")
                return True

        # Extract text
        logger.info(f"Processing: {file_path.name}")
        text, text_metadata = extractor.extract(file_path)

        if not text:
            logger.warning(f"No text extracted from {file_path.name}")
            error_msg = text_metadata.get('error', 'Unknown error')

            # Save to metadata DB as failed
            book_id = metadata_db.add_book(
                file_path=str(file_path),
                status='failed',
                error_message=error_msg
            )
            metadata_db.log_processing('extract_text', 'failed', book_id, error_msg)
            return False

        # Validate text
        min_length = config.get('processing.min_text_length', 100)
        if len(text) < min_length:
            logger.warning(f"Text too short ({len(text)} chars): {file_path.name}")
            book_id = metadata_db.add_book(
                file_path=str(file_path),
                status='failed',
                error_message=f'Text too short: {len(text)} chars'
            )
            return False

        # Add book to metadata DB
        book_id = metadata_db.add_book(
            file_path=str(file_path),
            title=text_metadata.get('title', file_path.stem),
            author=text_metadata.get('author', 'Unknown'),
            detected_language=text_metadata.get('detected_language'),
            total_words=text_metadata.get('word_count'),
            total_chars=text_metadata.get('char_count'),
            extraction_time=text_metadata.get('extraction_time'),
            status='processing'
        )

        logger.info(f"Extracted {text_metadata.get('word_count', 0)} words from {file_path.name}")

        # Chunk text
        perf.start("chunking")
        book_metadata = {
            'book_id': book_id,
            'book_title': text_metadata.get('title', file_path.stem),
            'book_author': text_metadata.get('author', 'Unknown'),
            'file_path': str(file_path)
        }

        chunks = chunker.chunk_text(text, book_metadata)
        perf.end("chunking", f"{len(chunks)} chunks created")

        if not chunks:
            logger.warning(f"No chunks created for {file_path.name}")
            metadata_db.update_book(book_id, status='failed', error_message='No chunks created')
            return False

        # Generate embeddings
        perf.start("embedding")
        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedder.encode(chunk_texts, show_progress=False)

        embedding_time = perf.end("embedding")

        # Add to vector database
        perf.start("vector_db_add")

        # Prepare metadata for vector DB
        vector_metadata = []
        for i, chunk in enumerate(chunks):
            vector_metadata.append({
                'book_id': book_id,
                'chunk_index': i,
                'book_title': book_metadata['book_title'],
                'book_author': book_metadata['book_author']
            })

        # Get starting vector ID
        start_vector_id = vector_db.size()

        # Add to vector DB
        vector_db.add(embeddings, vector_metadata)
        perf.end("vector_db_add", f"{len(embeddings)} vectors added")

        # Add chunks to metadata DB
        perf.start("metadata_db_add")
        for i, chunk in enumerate(chunks):
            vector_id = start_vector_id + i
            metadata_db.add_chunk(
                book_id=book_id,
                chunk_index=i,
                chunk_text=chunk.text,
                vector_id=vector_id,
                start_pos=chunk.start_pos,
                end_pos=chunk.end_pos
            )

        perf.end("metadata_db_add", f"{len(chunks)} chunks added")

        # Update book status
        metadata_db.update_book(
            book_id,
            chunk_count=len(chunks),
            embedding_time=embedding_time,
            status='completed'
        )

        # Log success
        metadata_db.log_processing('process_book', 'success', book_id)

        total_time = perf.end("process_book")
        logger.info(f"Successfully processed {file_path.name} in {total_time:.2f}s")

        return True

    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {str(e)}")
        try:
            book_id = metadata_db.add_book(
                file_path=str(file_path),
                status='failed',
                error_message=str(e)
            )
            metadata_db.log_processing('process_book', 'error', book_id, str(e))
        except:
            pass
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Build vector database from book collection"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--books-dir',
        type=str,
        help='Override books directory'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Override vector DB output path'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Reprocess all books (ignore skip_existing)'
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(args.config)

    # Initialize logger
    logger = init_global_logger(config)
    logger.info("=" * 60)
    logger.info("AI Library Vector Base Builder")
    logger.info("=" * 60)

    # Override config if specified
    if args.books_dir:
        config.set('paths.books', args.books_dir)

    if args.output:
        config.set('paths.vector_db', args.output)

    if args.force:
        config.set('processing.skip_existing', False)

    # Get paths
    books_path = config.books_path
    vector_db_path = config.vector_db_path
    metadata_db_path = config.metadata_db_path

    logger.info(f"Books directory: {books_path}")
    logger.info(f"Vector DB path: {vector_db_path}")
    logger.info(f"Metadata DB path: {metadata_db_path}")

    # Check books directory
    if not books_path.exists():
        logger.error(f"Books directory not found: {books_path}")
        logger.info("Please add books to the directory and try again.")
        return 1

    # Get book files
    supported_formats = config.get_supported_formats()
    book_files = []

    for format_ext in supported_formats:
        book_files.extend(books_path.glob(f"**/*{format_ext}"))

    if not book_files:
        logger.warning(f"No books found in {books_path}")
        logger.info(f"Supported formats: {', '.join(supported_formats)}")
        return 0

    logger.info(f"Found {len(book_files)} books to process")

    # Initialize components
    logger.info("Initializing components...")

    # Metadata DB
    metadata_db = MetadataDB(str(metadata_db_path))

    # Text extractor
    extractor = TextExtractor(logger=logger)

    # Text chunker
    chunker = TextChunker(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        min_chunk_size=config.get('chunking.min_chunk_size', 200),
        max_chunk_size=config.get('chunking.max_chunk_size', 1500),
        respect_paragraphs=config.get('chunking.respect_paragraphs', True),
        respect_sentences=config.get('chunking.respect_sentences', True),
        logger=logger
    )

    # Embedder
    logger.info("Loading embedding model...")
    embedder = create_embedder(
        model_name=config.embedding_model,
        device=config.embedding_device,
        batch_size=config.embedding_batch_size,
        cache_dir=config.get('embedding.cache_dir'),
        logger=logger
    )

    embedding_dim = embedder.get_embedding_dim()

    # Vector DB - load existing or create new
    if vector_db_path.with_suffix('.index').exists():
        logger.info("Loading existing vector database...")
        vector_db = VectorDB.load(str(vector_db_path), logger=logger)
    else:
        logger.info("Creating new vector database...")
        vector_db = VectorDB(
            dimension=embedding_dim,
            index_type=config.get('vector_db.index_type', 'IndexFlatIP'),
            normalize=config.get('vector_db.normalize', True),
            logger=logger
        )

    logger.info("Components initialized successfully")
    logger.info("")

    # Process books
    logger.info(f"Processing {len(book_files)} books...")
    successful = 0
    failed = 0
    skipped = 0

    perf = PerformanceLogger(logger)
    perf.start("total_processing")

    for book_file in tqdm(book_files, desc="Processing books"):
        result = process_book(
            book_file,
            extractor,
            chunker,
            embedder,
            vector_db,
            metadata_db,
            config,
            logger
        )

        if result:
            successful += 1
        else:
            # Check if it was skipped
            book_data = metadata_db.get_book_by_path(str(book_file))
            if book_data and book_data['status'] == 'completed' and result:
                skipped += 1
            else:
                failed += 1

        # Periodic save
        save_interval = config.get('vector_db.save_interval', 1000)
        if (successful + failed) % save_interval == 0:
            logger.info("Saving checkpoint...")
            vector_db.save(str(vector_db_path))

    total_time = perf.end("total_processing")

    # Save final vector database
    logger.info("")
    logger.info("Saving vector database...")
    vector_db.save(str(vector_db_path))

    # Print statistics
    logger.info("")
    logger.info("=" * 60)
    logger.info("Processing Complete!")
    logger.info("=" * 60)
    logger.info(f"Total books: {len(book_files)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"Vector database size: {vector_db.size()} vectors")

    # Database statistics
    db_stats = metadata_db.get_stats()
    logger.info("")
    logger.info("Database Statistics:")
    logger.info(f"  Total books: {db_stats['total_books']}")
    logger.info(f"  Total chunks: {db_stats['total_chunks']}")
    logger.info(f"  Total words: {db_stats['total_words']:,}")
    logger.info(f"  Avg extraction time: {db_stats['avg_extraction_time']:.2f}s")
    logger.info(f"  Avg embedding time: {db_stats['avg_embedding_time']:.2f}s")

    if db_stats['books_by_status']:
        logger.info(f"  Books by status: {db_stats['books_by_status']}")

    logger.info("")
    logger.info(f"Vector database saved to: {vector_db_path}")
    logger.info(f"Metadata database saved to: {metadata_db_path}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
