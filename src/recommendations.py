"""Book recommendation system based on semantic similarity."""

import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict


class BookRecommender:
    """Recommend books based on similarity and user interactions."""

    def __init__(self, embedder, vector_db, metadata_db, logger=None):
        """Initialize recommender.

        Args:
            embedder: Embedder instance
            vector_db: VectorDB instance
            metadata_db: MetadataDB instance
            logger: Optional logger
        """
        self.embedder = embedder
        self.vector_db = vector_db
        self.metadata_db = metadata_db
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def recommend_similar_books(
        self,
        book_id: int,
        n: int = 5,
        diversity_factor: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Recommend books similar to a given book.

        Args:
            book_id: Source book ID
            n: Number of recommendations
            diversity_factor: Balance between similarity and diversity (0-1)

        Returns:
            List of recommended books with scores
        """
        # Get all chunks for this book
        chunks = self.metadata_db.get_chunks(book_id)
        if not chunks:
            self._log('warning', f"No chunks found for book {book_id}")
            return []

        # Get average embedding for the book
        chunk_embeddings = []
        for chunk in chunks[:20]:  # Sample first 20 chunks
            if chunk['vector_id'] is not None:
                # Get embedding from vector DB
                # For now, we'll use a different approach
                pass

        # Alternative: search with representative chunk
        representative_chunk = chunks[len(chunks) // 2]  # Middle chunk
        chunk_text = representative_chunk['chunk_text']

        # Encode and search
        query_embedding = self.embedder.encode(chunk_text, show_progress=False)
        results = self.vector_db.search(query_embedding, k=n * 10)

        # Aggregate by book
        book_scores = defaultdict(list)
        for vec_id, score, metadata in results:
            if metadata and 'book_id' in metadata:
                result_book_id = metadata['book_id']
                if result_book_id != book_id:  # Exclude source book
                    book_scores[result_book_id].append(score)

        # Calculate average scores
        recommendations = []
        for rec_book_id, scores in book_scores.items():
            avg_score = np.mean(scores)
            book_data = self.metadata_db.get_book(rec_book_id)

            if book_data:
                recommendations.append({
                    'book_id': rec_book_id,
                    'title': book_data.get('title', 'Unknown'),
                    'author': book_data.get('author', 'Unknown'),
                    'similarity_score': float(avg_score),
                    'chunk_count': book_data.get('chunk_count', 0),
                    'language': book_data.get('detected_language', 'unknown'),
                })

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)

        self._log('info', f"Generated {len(recommendations[:n])} recommendations for book {book_id}")
        return recommendations[:n]

    def recommend_by_topic(
        self,
        topic: str,
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend books related to a topic.

        Args:
            topic: Topic description
            n: Number of recommendations

        Returns:
            List of recommended books
        """
        # Encode topic
        topic_embedding = self.embedder.encode(topic, show_progress=False)

        # Search for relevant chunks
        results = self.vector_db.search(topic_embedding, k=n * 5)

        # Aggregate by book
        book_scores = defaultdict(list)
        for vec_id, score, metadata in results:
            if metadata and 'book_id' in metadata:
                book_id = metadata['book_id']
                book_scores[book_id].append(score)

        # Get books with highest average scores
        recommendations = []
        for book_id, scores in book_scores.items():
            avg_score = np.mean(scores)
            book_data = self.metadata_db.get_book(book_id)

            if book_data:
                recommendations.append({
                    'book_id': book_id,
                    'title': book_data.get('title', 'Unknown'),
                    'author': book_data.get('author', 'Unknown'),
                    'similarity_score': float(avg_score),
                    'relevance': float(max(scores)),
                    'chunk_matches': len(scores),
                })

        # Sort by score
        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)

        self._log('info', f"Found {len(recommendations[:n])} books for topic: {topic}")
        return recommendations[:n]

    def recommend_by_author(
        self,
        author: str,
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """Recommend books by a specific author.

        Args:
            author: Author name
            n: Number of recommendations

        Returns:
            List of books by the author
        """
        # Get all books
        all_books = self.metadata_db.list_books()

        # Filter by author (case-insensitive partial match)
        author_lower = author.lower()
        matching_books = [
            book for book in all_books
            if book.get('author', '').lower().find(author_lower) != -1
        ]

        # Sort by word count (assuming longer = more substantial)
        matching_books.sort(
            key=lambda x: x.get('total_words', 0),
            reverse=True
        )

        recommendations = [
            {
                'book_id': book['id'],
                'title': book.get('title', 'Unknown'),
                'author': book.get('author', 'Unknown'),
                'word_count': book.get('total_words', 0),
                'chunk_count': book.get('chunk_count', 0),
            }
            for book in matching_books[:n]
        ]

        self._log('info', f"Found {len(recommendations)} books by {author}")
        return recommendations

    def recommend_by_reading_history(
        self,
        read_book_ids: List[int],
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend books based on reading history.

        Args:
            read_book_ids: List of book IDs user has read
            n: Number of recommendations

        Returns:
            List of recommended books
        """
        if not read_book_ids:
            return []

        # Collect all recommendations from read books
        all_recommendations = []
        for book_id in read_book_ids:
            recs = self.recommend_similar_books(book_id, n=10)
            all_recommendations.extend(recs)

        # Aggregate by book ID
        book_scores = defaultdict(list)
        book_info = {}

        for rec in all_recommendations:
            book_id = rec['book_id']
            if book_id not in read_book_ids:  # Exclude already read
                book_scores[book_id].append(rec['similarity_score'])
                book_info[book_id] = rec

        # Calculate average scores
        final_recommendations = []
        for book_id, scores in book_scores.items():
            rec = book_info[book_id].copy()
            rec['avg_similarity'] = float(np.mean(scores))
            rec['recommendation_count'] = len(scores)
            final_recommendations.append(rec)

        # Sort by average similarity and frequency
        final_recommendations.sort(
            key=lambda x: (x['avg_similarity'], x['recommendation_count']),
            reverse=True
        )

        self._log('info', f"Generated {len(final_recommendations[:n])} recommendations from reading history")
        return final_recommendations[:n]

    def get_diverse_recommendations(
        self,
        n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get a diverse set of books from the library.

        Args:
            n: Number of recommendations

        Returns:
            List of diverse books
        """
        all_books = self.metadata_db.list_books(status='completed')

        if not all_books:
            return []

        # Group by language and format for diversity
        by_language = defaultdict(list)
        by_format = defaultdict(list)

        for book in all_books:
            lang = book.get('detected_language', 'unknown')
            fmt = book.get('format', 'unknown')
            by_language[lang].append(book)
            by_format[fmt].append(book)

        # Select diverse books
        recommendations = []
        selected_ids = set()

        # Try to get at least one from each language
        for lang, books in sorted(by_language.items(), key=lambda x: len(x[1]), reverse=True):
            if len(recommendations) >= n:
                break

            # Get highest word count book from this language
            books_sorted = sorted(books, key=lambda x: x.get('total_words', 0), reverse=True)
            for book in books_sorted:
                if book['id'] not in selected_ids:
                    recommendations.append({
                        'book_id': book['id'],
                        'title': book.get('title', 'Unknown'),
                        'author': book.get('author', 'Unknown'),
                        'language': lang,
                        'format': book.get('format'),
                        'word_count': book.get('total_words', 0),
                    })
                    selected_ids.add(book['id'])
                    break

        # Fill remaining with highest word count
        if len(recommendations) < n:
            remaining = [b for b in all_books if b['id'] not in selected_ids]
            remaining.sort(key=lambda x: x.get('total_words', 0), reverse=True)

            for book in remaining[:n - len(recommendations)]:
                recommendations.append({
                    'book_id': book['id'],
                    'title': book.get('title', 'Unknown'),
                    'author': book.get('author', 'Unknown'),
                    'language': book.get('detected_language', 'unknown'),
                    'format': book.get('format'),
                    'word_count': book.get('total_words', 0),
                })

        self._log('info', f"Generated {len(recommendations)} diverse recommendations")
        return recommendations[:n]
