"""Advanced search filters for the AI Library."""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import re


class SearchFilter:
    """Advanced search filtering."""

    def __init__(self, metadata_db):
        """Initialize search filter.

        Args:
            metadata_db: MetadataDB instance
        """
        self.metadata_db = metadata_db

    def filter_books(
        self,
        format: Optional[str] = None,
        language: Optional[str] = None,
        author: Optional[str] = None,
        title: Optional[str] = None,
        min_words: Optional[int] = None,
        max_words: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter books by various criteria.

        Args:
            format: File format filter
            language: Language code filter
            author: Author name (partial match)
            title: Title (partial match)
            min_words: Minimum word count
            max_words: Maximum word count
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            status: Processing status

        Returns:
            Filtered list of books
        """
        books = self.metadata_db.list_books(status=status)

        filtered = books

        # Apply filters
        if format:
            filtered = [b for b in filtered if b.get('format') == format]

        if language:
            filtered = [b for b in filtered if b.get('detected_language') == language]

        if author:
            author_lower = author.lower()
            filtered = [
                b for b in filtered
                if b.get('author', '').lower().find(author_lower) != -1
            ]

        if title:
            title_lower = title.lower()
            filtered = [
                b for b in filtered
                if b.get('title', '').lower().find(title_lower) != -1
            ]

        if min_words is not None:
            filtered = [
                b for b in filtered
                if (b.get('total_words') or 0) >= min_words
            ]

        if max_words is not None:
            filtered = [
                b for b in filtered
                if (b.get('total_words') or 0) <= max_words
            ]

        if date_from:
            filtered = [
                b for b in filtered
                if b.get('created_at', '') >= date_from
            ]

        if date_to:
            filtered = [
                b for b in filtered
                if b.get('created_at', '') <= date_to
            ]

        return filtered

    def search_by_keywords(
        self,
        keywords: List[str],
        match_all: bool = False
    ) -> List[Dict[str, Any]]:
        """Search books by keywords in title or content.

        Args:
            keywords: List of keywords
            match_all: If True, all keywords must match

        Returns:
            List of matching books
        """
        books = self.metadata_db.list_books(status='completed')
        matches = []

        for book in books:
            # Get some chunks for content search
            chunks = self.metadata_db.get_chunks(book['id'])
            content = ' '.join(c['chunk_text'] for c in chunks[:5])  # First 5 chunks
            content += ' ' + book.get('title', '') + ' ' + book.get('author', '')
            content_lower = content.lower()

            # Check keyword matches
            keyword_matches = sum(1 for kw in keywords if kw.lower() in content_lower)

            if match_all:
                if keyword_matches == len(keywords):
                    matches.append(book)
            else:
                if keyword_matches > 0:
                    book_copy = book.copy()
                    book_copy['keyword_match_count'] = keyword_matches
                    matches.append(book_copy)

        # Sort by match count if not match_all
        if not match_all:
            matches.sort(key=lambda x: x.get('keyword_match_count', 0), reverse=True)

        return matches

    def search_by_regex(
        self,
        pattern: str,
        field: str = 'title'
    ) -> List[Dict[str, Any]]:
        """Search books using regex pattern.

        Args:
            pattern: Regex pattern
            field: Field to search (title, author)

        Returns:
            List of matching books
        """
        books = self.metadata_db.list_books()
        regex = re.compile(pattern, re.IGNORECASE)

        matches = []
        for book in books:
            value = book.get(field, '')
            if value and regex.search(value):
                matches.append(book)

        return matches

    def get_books_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """Get books added in a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            List of books
        """
        return self.filter_books(date_from=start_date, date_to=end_date)

    def get_longest_books(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get N longest books by word count.

        Args:
            n: Number of books

        Returns:
            List of longest books
        """
        books = self.metadata_db.list_books(status='completed')
        books_with_words = [b for b in books if b.get('total_words')]
        books_with_words.sort(key=lambda x: x['total_words'], reverse=True)

        return books_with_words[:n]

    def get_shortest_books(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get N shortest books by word count.

        Args:
            n: Number of books

        Returns:
            List of shortest books
        """
        books = self.metadata_db.list_books(status='completed')
        books_with_words = [b for b in books if b.get('total_words')]
        books_with_words.sort(key=lambda x: x['total_words'])

        return books_with_words[:n]

    def group_books_by(self, field: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group books by a field.

        Args:
            field: Field name (format, language, author, etc.)

        Returns:
            Dictionary mapping field values to book lists
        """
        books = self.metadata_db.list_books()
        groups = {}

        for book in books:
            value = book.get(field, 'Unknown')
            if value not in groups:
                groups[value] = []
            groups[value].append(book)

        return groups


class CrossReferenceFinder:
    """Find cross-references and connections between books."""

    def __init__(self, metadata_db, embedder, vector_db):
        """Initialize cross-reference finder.

        Args:
            metadata_db: MetadataDB instance
            embedder: Embedder instance
            vector_db: VectorDB instance
        """
        self.metadata_db = metadata_db
        self.embedder = embedder
        self.vector_db = vector_db

    def find_related_passages(
        self,
        chunk_text: str,
        book_id: int,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find related passages from other books.

        Args:
            chunk_text: Reference chunk text
            book_id: Source book ID (to exclude)
            top_k: Number of results

        Returns:
            List of related passages
        """
        # Encode chunk
        embedding = self.embedder.encode(chunk_text, show_progress=False)

        # Search
        results = self.vector_db.search(embedding, k=top_k * 3)

        # Filter out same book and collect results
        related = []

        for vec_id, score, metadata in results:
            if metadata and metadata.get('book_id') != book_id:
                chunk = self.metadata_db.get_chunk_by_vector_id(vec_id)
                if chunk:
                    book = self.metadata_db.get_book(chunk['book_id'])
                    related.append({
                        'chunk_text': chunk['chunk_text'],
                        'book_id': chunk['book_id'],
                        'book_title': book.get('title', 'Unknown'),
                        'book_author': book.get('author', 'Unknown'),
                        'similarity_score': score,
                        'chunk_index': chunk['chunk_index'],
                    })

                if len(related) >= top_k:
                    break

        return related

    def find_common_themes(
        self,
        book_ids: List[int],
        top_k: int = 10
    ) -> List[str]:
        """Find common themes across books.

        Args:
            book_ids: List of book IDs
            top_k: Number of themes

        Returns:
            List of common keywords/themes
        """
        from collections import Counter
        from .advanced_features import TopicModeler

        modeler = TopicModeler(self.metadata_db)
        all_keywords = []

        for book_id in book_ids:
            keywords = modeler.extract_keywords(book_id, n=50)
            all_keywords.extend([kw for kw, _ in keywords])

        # Find most common across all books
        common = Counter(all_keywords)

        # Return keywords that appear in multiple books
        themes = [kw for kw, count in common.most_common(top_k * 2) if count > 1]

        return themes[:top_k]


class BookComparison:
    """Compare books and find similarities/differences."""

    def __init__(self, metadata_db):
        """Initialize book comparison.

        Args:
            metadata_db: MetadataDB instance
        """
        self.metadata_db = metadata_db

    def compare_books(
        self,
        book_id1: int,
        book_id2: int
    ) -> Dict[str, Any]:
        """Compare two books.

        Args:
            book_id1: First book ID
            book_id2: Second book ID

        Returns:
            Comparison dictionary
        """
        book1 = self.metadata_db.get_book(book_id1)
        book2 = self.metadata_db.get_book(book_id2)

        if not book1 or not book2:
            return {}

        return {
            'book1': {
                'id': book_id1,
                'title': book1.get('title'),
                'author': book1.get('author'),
                'word_count': book1.get('total_words'),
                'chunk_count': book1.get('chunk_count'),
                'language': book1.get('detected_language'),
            },
            'book2': {
                'id': book_id2,
                'title': book2.get('title'),
                'author': book2.get('author'),
                'word_count': book2.get('total_words'),
                'chunk_count': book2.get('chunk_count'),
                'language': book2.get('detected_language'),
            },
            'comparison': {
                'same_author': book1.get('author') == book2.get('author'),
                'same_language': book1.get('detected_language') == book2.get('detected_language'),
                'word_count_diff': abs((book1.get('total_words', 0) - book2.get('total_words', 0))),
                'relative_length': book1.get('total_words', 1) / max(book2.get('total_words', 1), 1),
            }
        }
