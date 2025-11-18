"""Advanced features: duplicates, quotes, entities, clustering."""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import Counter, defaultdict
import numpy as np


class DuplicateDetector:
    """Detect duplicate or near-duplicate books."""

    def __init__(self, metadata_db, similarity_threshold: float = 0.9):
        """Initialize duplicate detector.

        Args:
            metadata_db: MetadataDB instance
            similarity_threshold: Threshold for similarity (0-1)
        """
        self.metadata_db = metadata_db
        self.similarity_threshold = similarity_threshold

    def find_duplicates(self) -> List[List[Dict[str, Any]]]:
        """Find duplicate books.

        Returns:
            List of duplicate groups
        """
        books = self.metadata_db.list_books()

        # Group by file hash (exact duplicates)
        by_hash = defaultdict(list)
        for book in books:
            if book.get('file_hash'):
                by_hash[book['file_hash']].append(book)

        # Find hash-based duplicates
        duplicates = [group for group in by_hash.values() if len(group) > 1]

        # Find near-duplicates by title similarity
        for i, book1 in enumerate(books):
            for book2 in books[i + 1:]:
                if self._are_similar(book1, book2):
                    # Check if already in a group
                    found = False
                    for group in duplicates:
                        if book1 in group or book2 in group:
                            if book1 not in group:
                                group.append(book1)
                            if book2 not in group:
                                group.append(book2)
                            found = True
                            break

                    if not found:
                        duplicates.append([book1, book2])

        return duplicates

    def _are_similar(self, book1: Dict, book2: Dict) -> bool:
        """Check if two books are similar.

        Args:
            book1: First book
            book2: Second book

        Returns:
            True if similar
        """
        # Compare titles
        title1 = book1.get('title', '').lower()
        title2 = book2.get('title', '').lower()

        if not title1 or not title2:
            return False

        # Simple similarity check
        similarity = self._string_similarity(title1, title2)

        # Also check author
        author1 = book1.get('author', '').lower()
        author2 = book2.get('author', '').lower()

        if author1 and author2:
            author_similarity = self._string_similarity(author1, author2)
            # Both title and author should be similar
            return similarity > 0.8 and author_similarity > 0.8

        return similarity > self.similarity_threshold

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (simple approach).

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0-1)
        """
        # Normalize
        s1 = re.sub(r'[^\w\s]', '', s1)
        s2 = re.sub(r'[^\w\s]', '', s2)

        # Character overlap
        set1 = set(s1.split())
        set2 = set(s2.split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


class QuoteExtractor:
    """Extract notable quotes from books."""

    def __init__(self, metadata_db, logger=None):
        """Initialize quote extractor.

        Args:
            metadata_db: MetadataDB instance
            logger: Optional logger
        """
        self.metadata_db = metadata_db
        self.logger = logger

    def extract_quotes(
        self,
        book_id: int,
        min_length: int = 50,
        max_length: int = 500
    ) -> List[Dict[str, Any]]:
        """Extract potential quotes from a book.

        Args:
            book_id: Book ID
            min_length: Minimum quote length
            max_length: Maximum quote length

        Returns:
            List of quote dictionaries
        """
        chunks = self.metadata_db.get_chunks(book_id)
        book = self.metadata_db.get_book(book_id)

        if not chunks or not book:
            return []

        quotes = []

        for chunk in chunks:
            text = chunk['chunk_text']

            # Find quoted text
            quoted_texts = re.findall(r'"([^"]{' + str(min_length) + ',' + str(max_length) + '})"', text)
            quoted_texts += re.findall(r'"([^"]{' + str(min_length) + ',' + str(max_length) + '})"', text)

            for quote_text in quoted_texts:
                quotes.append({
                    'text': quote_text.strip(),
                    'book_id': book_id,
                    'book_title': book.get('title', 'Unknown'),
                    'book_author': book.get('author', 'Unknown'),
                    'chunk_index': chunk['chunk_index'],
                    'length': len(quote_text),
                })

        return quotes

    def extract_key_sentences(
        self,
        book_id: int,
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """Extract key sentences from a book.

        Args:
            book_id: Book ID
            n: Number of sentences to extract

        Returns:
            List of sentence dictionaries
        """
        chunks = self.metadata_db.get_chunks(book_id)
        book = self.metadata_db.get_book(book_id)

        if not chunks or not book:
            return []

        # Simple heuristic: sentences with important words
        important_words = {
            'important', 'crucial', 'essential', 'fundamental', 'key',
            'must', 'should', 'always', 'never', 'believe', 'think',
            'conclude', 'argue', 'suggest', 'propose', 'demonstrate'
        }

        sentences = []

        for chunk in chunks:
            text = chunk['chunk_text']

            # Split into sentences
            chunk_sentences = re.split(r'[.!?]+', text)

            for sentence in chunk_sentences:
                sentence = sentence.strip()

                if len(sentence) < 50 or len(sentence) > 500:
                    continue

                # Count important words
                words = set(sentence.lower().split())
                importance_score = len(words & important_words)

                if importance_score > 0:
                    sentences.append({
                        'text': sentence,
                        'book_id': book_id,
                        'book_title': book.get('title', 'Unknown'),
                        'book_author': book.get('author', 'Unknown'),
                        'chunk_index': chunk['chunk_index'],
                        'importance_score': importance_score,
                    })

        # Sort by importance
        sentences.sort(key=lambda x: x['importance_score'], reverse=True)

        return sentences[:n]


class NamedEntityExtractor:
    """Extract named entities from text (simple rule-based)."""

    def __init__(self):
        """Initialize NER."""
        self.person_indicators = {'mr.', 'mrs.', 'ms.', 'dr.', 'prof.'}
        self.location_indicators = {'city', 'town', 'country', 'state', 'province'}

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text.

        Args:
            text: Input text

        Returns:
            Dictionary of entity types and entities
        """
        entities = {
            'PERSON': [],
            'LOCATION': [],
            'ORGANIZATION': [],
            'DATE': [],
        }

        # Find capitalized phrases (simple approach)
        capitalized_phrases = re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b', text)

        entities['PERSON'] = list(set(capitalized_phrases))

        # Find dates
        dates = re.findall(r'\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b', text)
        entities['DATE'] = list(set(dates))

        return entities


class TopicModeler:
    """Simple topic modeling using keyword extraction."""

    def __init__(self, metadata_db):
        """Initialize topic modeler.

        Args:
            metadata_db: MetadataDB instance
        """
        self.metadata_db = metadata_db

        # Common stop words
        self.stop_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
            'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
            'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
            'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
            'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out',
            'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when',
        }

    def extract_keywords(
        self,
        book_id: int,
        n: int = 20,
        min_word_length: int = 4
    ) -> List[Tuple[str, int]]:
        """Extract keywords from a book.

        Args:
            book_id: Book ID
            n: Number of keywords
            min_word_length: Minimum word length

        Returns:
            List of (keyword, frequency) tuples
        """
        chunks = self.metadata_db.get_chunks(book_id)

        if not chunks:
            return []

        # Collect all words
        all_words = []

        for chunk in chunks:
            text = chunk['chunk_text'].lower()
            # Remove punctuation
            text = re.sub(r'[^\w\s]', ' ', text)
            words = text.split()

            # Filter words
            words = [
                w for w in words
                if len(w) >= min_word_length and w not in self.stop_words
            ]

            all_words.extend(words)

        # Count frequencies
        word_freq = Counter(all_words)

        return word_freq.most_common(n)

    def cluster_books_by_keywords(
        self,
        n_clusters: int = 5
    ) -> Dict[int, List[int]]:
        """Cluster books by keyword similarity.

        Args:
            n_clusters: Number of clusters

        Returns:
            Dictionary mapping cluster ID to book IDs
        """
        books = self.metadata_db.list_books(status='completed')

        if not books:
            return {}

        # Extract keywords for each book
        book_keywords = {}

        for book in books[:50]:  # Limit for performance
            keywords = self.extract_keywords(book['id'], n=50)
            book_keywords[book['id']] = set(kw for kw, _ in keywords)

        # Simple clustering based on keyword overlap
        clusters = defaultdict(list)
        assigned = set()

        cluster_id = 0

        for book_id, keywords in book_keywords.items():
            if book_id in assigned:
                continue

            # Start new cluster
            clusters[cluster_id].append(book_id)
            assigned.add(book_id)

            # Find similar books
            for other_id, other_keywords in book_keywords.items():
                if other_id in assigned:
                    continue

                # Calculate overlap
                overlap = len(keywords & other_keywords)
                union = len(keywords | other_keywords)

                if overlap / max(union, 1) > 0.3:  # 30% similarity
                    clusters[cluster_id].append(other_id)
                    assigned.add(other_id)

            cluster_id += 1

            if cluster_id >= n_clusters:
                break

        return dict(clusters)


class BookmarkManager:
    """Manage bookmarks and highlights."""

    def __init__(self, db_path: str = "./data/bookmarks.db"):
        """Initialize bookmark manager.

        Args:
            db_path: Path to SQLite database
        """
        import sqlite3
        from pathlib import Path

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chunk_id INTEGER,
                    note TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reading_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reading_list_items (
                    list_id INTEGER,
                    book_id INTEGER,
                    position INTEGER,
                    completed BOOLEAN DEFAULT 0,
                    FOREIGN KEY (list_id) REFERENCES reading_lists(id),
                    PRIMARY KEY (list_id, book_id)
                )
            """)

    def add_bookmark(
        self,
        book_id: int,
        chunk_id: int = None,
        note: str = None,
        tags: List[str] = None
    ) -> int:
        """Add a bookmark.

        Args:
            book_id: Book ID
            chunk_id: Optional chunk ID
            note: Optional note
            tags: Optional tags

        Returns:
            Bookmark ID
        """
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookmarks (book_id, chunk_id, note, tags)
                VALUES (?, ?, ?, ?)
            """, (
                book_id,
                chunk_id,
                note,
                ','.join(tags) if tags else None
            ))

            return cursor.lastrowid

    def get_bookmarks(self, book_id: int = None) -> List[Dict[str, Any]]:
        """Get bookmarks.

        Args:
            book_id: Optional filter by book

        Returns:
            List of bookmarks
        """
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if book_id:
                cursor.execute("""
                    SELECT * FROM bookmarks WHERE book_id = ?
                    ORDER BY created_at DESC
                """, (book_id,))
            else:
                cursor.execute("""
                    SELECT * FROM bookmarks ORDER BY created_at DESC
                """)

            return [dict(row) for row in cursor.fetchall()]

    def create_reading_list(self, name: str, description: str = None) -> int:
        """Create a reading list.

        Args:
            name: List name
            description: Optional description

        Returns:
            List ID
        """
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reading_lists (name, description)
                VALUES (?, ?)
            """, (name, description))

            return cursor.lastrowid

    def add_to_reading_list(self, list_id: int, book_id: int) -> None:
        """Add book to reading list.

        Args:
            list_id: Reading list ID
            book_id: Book ID
        """
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            # Get max position
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(position) FROM reading_list_items WHERE list_id = ?
            """, (list_id,))

            max_pos = cursor.fetchone()[0] or 0

            cursor.execute("""
                INSERT OR IGNORE INTO reading_list_items (list_id, book_id, position)
                VALUES (?, ?, ?)
            """, (list_id, book_id, max_pos + 1))

    def get_reading_list(self, list_id: int) -> Dict[str, Any]:
        """Get a reading list with books.

        Args:
            list_id: List ID

        Returns:
            Reading list dictionary
        """
        import sqlite3

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM reading_lists WHERE id = ?
            """, (list_id,))

            list_data = dict(cursor.fetchone())

            cursor.execute("""
                SELECT * FROM reading_list_items
                WHERE list_id = ?
                ORDER BY position
            """, (list_id,))

            list_data['items'] = [dict(row) for row in cursor.fetchall()]

            return list_data
