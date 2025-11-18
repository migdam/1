"""Enhanced statistics and analytics for the AI Library."""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json


class LibraryAnalytics:
    """Advanced analytics and statistics for the library."""

    def __init__(self, metadata_db, vector_db, logger=None):
        """Initialize analytics.

        Args:
            metadata_db: MetadataDB instance
            vector_db: VectorDB instance
            logger: Optional logger
        """
        self.metadata_db = metadata_db
        self.vector_db = vector_db
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive library statistics.

        Returns:
            Dictionary with detailed statistics
        """
        stats = {
            'overview': self._get_overview_stats(),
            'books': self._get_book_stats(),
            'processing': self._get_processing_stats(),
            'content': self._get_content_stats(),
            'quality': self._get_quality_metrics(),
            'growth': self._get_growth_metrics(),
        }
        return stats

    def _get_overview_stats(self) -> Dict[str, Any]:
        """Get overview statistics."""
        base_stats = self.metadata_db.get_stats()

        return {
            'total_books': base_stats['total_books'],
            'total_chunks': base_stats['total_chunks'],
            'total_words': base_stats['total_words'],
            'total_vectors': self.vector_db.size(),
            'avg_chunks_per_book': base_stats['total_chunks'] / max(base_stats['total_books'], 1),
            'avg_words_per_book': base_stats['total_words'] / max(base_stats['total_books'], 1),
        }

    def _get_book_stats(self) -> Dict[str, Any]:
        """Get book-level statistics."""
        books = self.metadata_db.list_books()

        if not books:
            return {}

        formats = Counter(book['format'] for book in books)
        languages = Counter(book.get('detected_language', 'unknown') for book in books)
        statuses = Counter(book['status'] for book in books)

        chunk_counts = [book['chunk_count'] for book in books if book['chunk_count']]
        word_counts = [book['total_words'] for book in books if book['total_words']]

        return {
            'by_format': dict(formats),
            'by_language': dict(languages),
            'by_status': dict(statuses),
            'chunk_distribution': {
                'min': min(chunk_counts) if chunk_counts else 0,
                'max': max(chunk_counts) if chunk_counts else 0,
                'avg': sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0,
            },
            'word_distribution': {
                'min': min(word_counts) if word_counts else 0,
                'max': max(word_counts) if word_counts else 0,
                'avg': sum(word_counts) / len(word_counts) if word_counts else 0,
            },
        }

    def _get_processing_stats(self) -> Dict[str, Any]:
        """Get processing performance statistics."""
        books = self.metadata_db.list_books()

        extraction_times = [b['extraction_time'] for b in books if b.get('extraction_time')]
        embedding_times = [b['embedding_time'] for b in books if b.get('embedding_time')]

        return {
            'extraction': {
                'avg_time': sum(extraction_times) / len(extraction_times) if extraction_times else 0,
                'total_time': sum(extraction_times),
                'min_time': min(extraction_times) if extraction_times else 0,
                'max_time': max(extraction_times) if extraction_times else 0,
            },
            'embedding': {
                'avg_time': sum(embedding_times) / len(embedding_times) if embedding_times else 0,
                'total_time': sum(embedding_times),
                'min_time': min(embedding_times) if embedding_times else 0,
                'max_time': max(embedding_times) if embedding_times else 0,
            },
        }

    def _get_content_stats(self) -> Dict[str, Any]:
        """Get content-related statistics."""
        books = self.metadata_db.list_books()

        total_chars = sum(b['total_chars'] for b in books if b.get('total_chars'))
        total_words = sum(b['total_words'] for b in books if b.get('total_words'))

        return {
            'total_characters': total_chars,
            'total_words': total_words,
            'avg_word_length': total_chars / max(total_words, 1),
            'estimated_pages': total_words / 250,  # ~250 words per page
            'estimated_reading_hours': total_words / 12000,  # ~200 words per minute
        }

    def _get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics."""
        books = self.metadata_db.list_books()

        completed = len([b for b in books if b['status'] == 'completed'])
        failed = len([b for b in books if b['status'] == 'failed'])

        return {
            'success_rate': completed / max(len(books), 1),
            'failure_rate': failed / max(len(books), 1),
            'completion_rate': completed / max(len(books), 1),
        }

    def _get_growth_metrics(self) -> Dict[str, Any]:
        """Get growth metrics over time."""
        books = self.metadata_db.list_books()

        if not books:
            return {}

        # Group by date
        books_by_date = defaultdict(int)
        for book in books:
            if book.get('created_at'):
                date = book['created_at'].split('T')[0]
                books_by_date[date] += 1

        recent_7_days = sum(
            count for date, count in books_by_date.items()
            if date >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        )

        recent_30_days = sum(
            count for date, count in books_by_date.items()
            if date >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        )

        return {
            'books_last_7_days': recent_7_days,
            'books_last_30_days': recent_30_days,
            'daily_average': len(books) / max(len(books_by_date), 1),
        }

    def get_top_books(self, n: int = 10, metric: str = 'words') -> List[Dict[str, Any]]:
        """Get top N books by a metric.

        Args:
            n: Number of books
            metric: Metric to sort by (words, chunks, chars)

        Returns:
            List of top books
        """
        books = self.metadata_db.list_books()

        metric_map = {
            'words': 'total_words',
            'chunks': 'chunk_count',
            'chars': 'total_chars',
        }

        key = metric_map.get(metric, 'total_words')
        sorted_books = sorted(
            books,
            key=lambda b: b.get(key, 0) or 0,
            reverse=True
        )

        return sorted_books[:n]

    def export_stats(self, filepath: str, format: str = 'json') -> None:
        """Export statistics to file.

        Args:
            filepath: Output file path
            format: Export format (json, txt)
        """
        stats = self.get_comprehensive_stats()

        if format == 'json':
            with open(filepath, 'w') as f:
                json.dump(stats, f, indent=2)
        elif format == 'txt':
            with open(filepath, 'w') as f:
                f.write("AI LIBRARY STATISTICS\n")
                f.write("=" * 60 + "\n\n")
                self._write_stats_text(f, stats)

        self._log('info', f"Exported statistics to {filepath}")

    def _write_stats_text(self, f, stats: Dict[str, Any], indent: int = 0) -> None:
        """Write statistics in text format."""
        prefix = "  " * indent

        for key, value in stats.items():
            if isinstance(value, dict):
                f.write(f"{prefix}{key.upper()}:\n")
                self._write_stats_text(f, value, indent + 1)
            else:
                f.write(f"{prefix}{key}: {value}\n")

    def generate_report(self) -> str:
        """Generate a formatted text report.

        Returns:
            Formatted report string
        """
        stats = self.get_comprehensive_stats()

        report = []
        report.append("=" * 60)
        report.append("AI LIBRARY ANALYTICS REPORT")
        report.append("=" * 60)
        report.append("")

        # Overview
        report.append("OVERVIEW")
        report.append("-" * 60)
        overview = stats['overview']
        report.append(f"Total Books: {overview['total_books']}")
        report.append(f"Total Chunks: {overview['total_chunks']}")
        report.append(f"Total Words: {overview['total_words']:,}")
        report.append(f"Total Vectors: {overview['total_vectors']}")
        report.append(f"Avg Chunks/Book: {overview['avg_chunks_per_book']:.1f}")
        report.append(f"Avg Words/Book: {overview['avg_words_per_book']:,.0f}")
        report.append("")

        # Content
        report.append("CONTENT STATISTICS")
        report.append("-" * 60)
        content = stats['content']
        report.append(f"Total Characters: {content['total_characters']:,}")
        report.append(f"Estimated Pages: {content['estimated_pages']:,.0f}")
        report.append(f"Estimated Reading Hours: {content['estimated_reading_hours']:,.1f}")
        report.append("")

        # Quality
        report.append("QUALITY METRICS")
        report.append("-" * 60)
        quality = stats['quality']
        report.append(f"Success Rate: {quality['success_rate']*100:.1f}%")
        report.append(f"Completion Rate: {quality['completion_rate']*100:.1f}%")
        report.append("")

        # Processing Performance
        report.append("PROCESSING PERFORMANCE")
        report.append("-" * 60)
        processing = stats['processing']
        report.append(f"Avg Extraction Time: {processing['extraction']['avg_time']:.2f}s")
        report.append(f"Avg Embedding Time: {processing['embedding']['avg_time']:.2f}s")
        report.append("")

        # Books by Format
        if 'books' in stats and 'by_format' in stats['books']:
            report.append("BOOKS BY FORMAT")
            report.append("-" * 60)
            for fmt, count in stats['books']['by_format'].items():
                report.append(f"  {fmt}: {count}")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)
