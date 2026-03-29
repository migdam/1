"""Text chunking utilities for semantic segmentation."""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""

    text: str
    index: int
    start_pos: int
    end_pos: int
    word_count: int
    char_count: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize calculated fields."""
        if self.metadata is None:
            self.metadata = {}
        self.word_count = len(self.text.split())
        self.char_count = len(self.text)


class TextChunker:
    """Chunk text into semantic segments."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        min_chunk_size: int = 200,
        max_chunk_size: int = 1500,
        respect_paragraphs: bool = True,
        respect_sentences: bool = True,
        logger=None
    ):
        """Initialize text chunker.

        Args:
            chunk_size: Target chunk size in words
            chunk_overlap: Overlap between chunks in words
            min_chunk_size: Minimum chunk size in words
            max_chunk_size: Maximum chunk size in words
            respect_paragraphs: Try to keep paragraphs intact
            respect_sentences: Try to keep sentences intact
            logger: Optional logger instance
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.respect_paragraphs = respect_paragraphs
        self.respect_sentences = respect_sentences
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def chunk_text(self, text: str, book_metadata: Dict[str, Any] = None) -> List[Chunk]:
        """Chunk text into semantic segments.

        Args:
            text: Text to chunk
            book_metadata: Optional book metadata to include

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        if book_metadata is None:
            book_metadata = {}

        self._log('debug', f"Chunking text of {len(text)} characters")

        if self.respect_paragraphs:
            chunks = self._chunk_by_paragraphs(text)
        elif self.respect_sentences:
            chunks = self._chunk_by_sentences(text)
        else:
            chunks = self._chunk_by_words(text)

        # Add book metadata to each chunk
        for chunk in chunks:
            chunk.metadata.update(book_metadata)

        self._log('info', f"Created {len(chunks)} chunks")
        return chunks

    def _chunk_by_paragraphs(self, text: str) -> List[Chunk]:
        """Chunk text by paragraphs, respecting chunk size limits.

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        # Split into paragraphs
        paragraphs = re.split(r'\n\n+', text)

        chunks = []
        current_chunk_parts = []
        current_word_count = 0
        char_position = 0
        chunk_start_pos = 0

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            para_word_count = len(para.split())

            # If single paragraph exceeds max size, split it
            if para_word_count > self.max_chunk_size:
                # Save current chunk if exists
                if current_chunk_parts:
                    chunk_text = '\n\n'.join(current_chunk_parts)
                    chunks.append(self._create_chunk(
                        chunk_text,
                        len(chunks),
                        chunk_start_pos,
                        chunk_start_pos + len(chunk_text)
                    ))
                    current_chunk_parts = []
                    current_word_count = 0

                # Split large paragraph by sentences
                sentence_chunks = self._chunk_by_sentences(para)
                for sent_chunk in sentence_chunks:
                    sent_chunk.index = len(chunks)
                    sent_chunk.start_pos += char_position
                    sent_chunk.end_pos += char_position
                    chunks.append(sent_chunk)

                char_position += len(para) + 2  # +2 for \n\n
                chunk_start_pos = char_position

                continue

            # Check if adding this paragraph would exceed chunk size
            if current_word_count + para_word_count > self.chunk_size and current_chunk_parts:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk_parts)
                chunks.append(self._create_chunk(
                    chunk_text,
                    len(chunks),
                    chunk_start_pos,
                    chunk_start_pos + len(chunk_text)
                ))

                # Handle overlap
                if self.chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(current_chunk_parts, self.chunk_overlap)
                    current_chunk_parts = [overlap_text] if overlap_text else []
                    current_word_count = len(overlap_text.split()) if overlap_text else 0
                else:
                    current_chunk_parts = []
                    current_word_count = 0

                chunk_start_pos = char_position

            # Add paragraph to current chunk
            current_chunk_parts.append(para)
            current_word_count += para_word_count
            char_position += len(para) + 2  # +2 for \n\n

        # Add final chunk
        if current_chunk_parts:
            chunk_text = '\n\n'.join(current_chunk_parts)
            chunks.append(self._create_chunk(
                chunk_text,
                len(chunks),
                chunk_start_pos,
                chunk_start_pos + len(chunk_text)
            ))

        # Filter out chunks that are too small (unless it's the only chunk)
        if len(chunks) > 1:
            chunks = [c for c in chunks if c.word_count >= self.min_chunk_size]

        return chunks

    def _chunk_by_sentences(self, text: str) -> List[Chunk]:
        """Chunk text by sentences, respecting chunk size limits.

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        # Split into sentences (simple regex - could be improved with NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk_parts = []
        current_word_count = 0
        char_position = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_word_count = len(sentence.split())

            # Check if adding this sentence would exceed chunk size
            if current_word_count + sentence_word_count > self.chunk_size and current_chunk_parts:
                # Save current chunk
                chunk_text = ' '.join(current_chunk_parts)
                chunks.append(self._create_chunk(
                    chunk_text,
                    len(chunks),
                    char_position - len(chunk_text),
                    char_position
                ))

                # Handle overlap
                if self.chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(current_chunk_parts, self.chunk_overlap)
                    current_chunk_parts = [overlap_text] if overlap_text else []
                    current_word_count = len(overlap_text.split()) if overlap_text else 0
                else:
                    current_chunk_parts = []
                    current_word_count = 0

            # Add sentence to current chunk
            current_chunk_parts.append(sentence)
            current_word_count += sentence_word_count
            char_position += len(sentence) + 1  # +1 for space

        # Add final chunk
        if current_chunk_parts:
            chunk_text = ' '.join(current_chunk_parts)
            chunks.append(self._create_chunk(
                chunk_text,
                len(chunks),
                char_position - len(chunk_text),
                char_position
            ))

        # Filter out chunks that are too small (unless it's the only chunk)
        if len(chunks) > 1:
            chunks = [c for c in chunks if c.word_count >= self.min_chunk_size]

        return chunks

    def _chunk_by_words(self, text: str) -> List[Chunk]:
        """Chunk text by word count (simple splitting).

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        words = text.split()
        chunks = []
        char_position = 0

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            chunks.append(self._create_chunk(
                chunk_text,
                len(chunks),
                char_position,
                char_position + len(chunk_text)
            ))

            char_position += len(chunk_text)

        return chunks

    def _create_chunk(
        self,
        text: str,
        index: int,
        start_pos: int,
        end_pos: int
    ) -> Chunk:
        """Create a Chunk object.

        Args:
            text: Chunk text
            index: Chunk index
            start_pos: Start position in original text
            end_pos: End position in original text

        Returns:
            Chunk object
        """
        return Chunk(
            text=text.strip(),
            index=index,
            start_pos=start_pos,
            end_pos=end_pos,
            word_count=len(text.split()),
            char_count=len(text)
        )

    def _get_overlap_text(self, parts: List[str], overlap_words: int) -> str:
        """Get overlap text from the end of parts.

        Args:
            parts: List of text parts
            overlap_words: Number of words to overlap

        Returns:
            Overlap text
        """
        if not parts:
            return ""

        # Join all parts and get last N words
        full_text = ' '.join(parts)
        words = full_text.split()

        if len(words) <= overlap_words:
            return full_text

        overlap_words_list = words[-overlap_words:]
        return ' '.join(overlap_words_list)


def chunk_book(
    text: str,
    book_metadata: Dict[str, Any] = None,
    config=None,
    logger=None
) -> List[Chunk]:
    """Convenience function to chunk a book's text.

    Args:
        text: Book text to chunk
        book_metadata: Optional book metadata
        config: Optional configuration object
        logger: Optional logger instance

    Returns:
        List of Chunk objects
    """
    if config:
        chunker = TextChunker(
            chunk_size=config.get('chunking.chunk_size', 1000),
            chunk_overlap=config.get('chunking.chunk_overlap', 100),
            min_chunk_size=config.get('chunking.min_chunk_size', 200),
            max_chunk_size=config.get('chunking.max_chunk_size', 1500),
            respect_paragraphs=config.get('chunking.respect_paragraphs', True),
            respect_sentences=config.get('chunking.respect_sentences', True),
            logger=logger
        )
    else:
        chunker = TextChunker(logger=logger)

    return chunker.chunk_text(text, book_metadata)
