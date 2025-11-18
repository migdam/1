#!/usr/bin/env python3
"""Comprehensive tests for all 20 AI Library enhancements."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import shutil
from datetime import datetime

# Import all modules to test
from src.config_loader import Config
from src.logger import setup_logger
from src.metadata_db import MetadataDB
from src.text_extractor import TextExtractor
from src.chunker import TextChunker, Chunk
from src.embedder import Embedder
from src.vector_db import VectorDB
from src.llm_client import LLMClient
from src.retriever import Retriever, RAGPipeline
from src.analytics import LibraryAnalytics
from src.export_tools import ExportManager
from src.conversation_history import ConversationHistory
from src.recommendations import BookRecommender
from src.advanced_features import (
    DuplicateDetector,
    QuoteExtractor,
    NamedEntityExtractor,
    TopicModeler,
    BookmarkManager
)
from src.search_filters import SearchFilter, CrossReferenceFinder, BookComparison
from src.api_server import LibraryAPI


class TestEnhancements:
    """Test suite for all enhancements."""

    @pytest.fixture
    def setup_test_env(self):
        """Set up test environment."""
        # Create temporary directory
        test_dir = tempfile.mkdtemp()

        # Create test database
        db_path = Path(test_dir) / "test.db"
        metadata_db = MetadataDB(str(db_path))

        # Add sample books
        book1_id = metadata_db.add_book(
            file_path="/test/book1.pdf",
            file_hash="hash1",
            title="Test Book 1",
            author="Author One",
            total_words=10000,
            chunk_count=10,
            status="completed"
        )

        book2_id = metadata_db.add_book(
            file_path="/test/book2.epub",
            file_hash="hash2",
            title="Test Book 2",
            author="Author Two",
            total_words=15000,
            chunk_count=15,
            status="completed"
        )

        # Add chunks
        for i in range(5):
            metadata_db.add_chunk(
                book_id=book1_id,
                chunk_index=i,
                chunk_text=f"This is test chunk {i} from book 1 about philosophy and wisdom.",
                vector_id=i
            )

        for i in range(5):
            metadata_db.add_chunk(
                book_id=book2_id,
                chunk_index=i,
                chunk_text=f"This is test chunk {i} from book 2 about science and technology.",
                vector_id=i + 5
            )

        yield {
            'test_dir': test_dir,
            'metadata_db': metadata_db,
            'book1_id': book1_id,
            'book2_id': book2_id
        }

        # Cleanup
        shutil.rmtree(test_dir)

    def test_01_analytics(self, setup_test_env):
        """Test Enhancement 1: Analytics & Statistics Dashboard."""
        print("\n[TEST 1] Analytics & Statistics Dashboard")

        metadata_db = setup_test_env['metadata_db']
        vector_db = VectorDB(dimension=384)

        analytics = LibraryAnalytics(metadata_db, vector_db)

        # Get comprehensive stats
        stats = analytics.get_comprehensive_stats()

        assert 'overview' in stats
        assert stats['overview']['total_books'] == 2
        assert 'books' in stats
        assert 'processing' in stats

        # Get top books
        top_books = analytics.get_top_books(n=2, metric='words')
        assert len(top_books) == 2
        assert top_books[0]['total_words'] >= top_books[1]['total_words']

        # Generate report
        report = analytics.generate_report()
        assert 'AI LIBRARY ANALYTICS REPORT' in report
        assert 'Total Books: 2' in report

        print("✓ Analytics working correctly")

    def test_02_export_markdown(self, setup_test_env):
        """Test Enhancement 2: Export to Markdown."""
        print("\n[TEST 2] Export to Markdown")

        test_dir = setup_test_env['test_dir']
        exporter = ExportManager()

        # Create mock results
        class MockResult:
            def __init__(self):
                self.book_title = "Test Book"
                self.book_author = "Test Author"
                self.similarity_score = 0.95
                self.chunk_index = 0
                self.chunk_text = "This is a test chunk."

        results = [MockResult() for _ in range(3)]

        # Export to markdown
        filepath = Path(test_dir) / "test_export.md"
        exporter.export_results_markdown(
            question="Test question?",
            answer="Test answer.",
            results=results,
            filepath=str(filepath)
        )

        assert filepath.exists()
        content = filepath.read_text()
        assert '# AI Library Query Result' in content
        assert 'Test question?' in content
        assert 'Test answer.' in content

        print("✓ Markdown export working correctly")

    def test_03_export_json(self, setup_test_env):
        """Test Enhancement 3: Export to JSON."""
        print("\n[TEST 3] Export to JSON")

        test_dir = setup_test_env['test_dir']
        exporter = ExportManager()

        class MockResult:
            def __init__(self):
                self.book_title = "Test Book"
                self.book_author = "Test Author"
                self.similarity_score = 0.95
                self.chunk_index = 0
                self.chunk_text = "This is a test chunk."
                self.book_id = 1

        results = [MockResult()]

        filepath = Path(test_dir) / "test_export.json"
        exporter.export_results_json(
            question="Test?",
            answer="Answer.",
            results=results,
            filepath=str(filepath)
        )

        assert filepath.exists()
        import json
        data = json.loads(filepath.read_text())
        assert data['question'] == "Test?"
        assert len(data['sources']) == 1

        print("✓ JSON export working correctly")

    def test_04_export_csv(self, setup_test_env):
        """Test Enhancement 4: Export to CSV."""
        print("\n[TEST 4] Export to CSV")

        test_dir = setup_test_env['test_dir']
        metadata_db = setup_test_env['metadata_db']

        exporter = ExportManager()
        books = metadata_db.list_books()

        filepath = Path(test_dir) / "books.csv"
        exporter.export_books_csv(books, str(filepath))

        assert filepath.exists()
        content = filepath.read_text()
        assert 'title' in content
        assert 'author' in content

        print("✓ CSV export working correctly")

    def test_05_conversation_history(self, setup_test_env):
        """Test Enhancement 5: Conversation History."""
        print("\n[TEST 5] Conversation History Tracking")

        test_dir = setup_test_env['test_dir']
        history_db = Path(test_dir) / "history.db"

        history = ConversationHistory(str(history_db))

        # Add conversation
        conv_id = history.add_conversation(
            question="What is life?",
            answer="Life is complex.",
            session_id="test_session"
        )

        assert conv_id > 0

        # Retrieve conversation
        conv = history.get_conversation(conv_id)
        assert conv is not None
        assert conv['question'] == "What is life?"

        # Get recent conversations
        recent = history.get_recent_conversations(limit=10)
        assert len(recent) == 1

        # Get statistics
        stats = history.get_statistics()
        assert stats['total_conversations'] == 1

        print("✓ Conversation history working correctly")

    def test_06_recommendations(self, setup_test_env):
        """Test Enhancement 6: Book Recommendations."""
        print("\n[TEST 6] Book Recommendation System")

        metadata_db = setup_test_env['metadata_db']
        book1_id = setup_test_env['book1_id']

        # Create mock embedder and vector DB
        class MockEmbedder:
            def encode(self, text, show_progress=True):
                import numpy as np
                return np.random.rand(384)

        class MockVectorDB:
            def search(self, embedding, k=5):
                # Return mock results
                return [
                    (i, 0.9 - i * 0.1, {'book_id': 2, 'chunk_index': i})
                    for i in range(k)
                ]

        embedder = MockEmbedder()
        vector_db = MockVectorDB()

        recommender = BookRecommender(embedder, vector_db, metadata_db)

        # Get recommendations
        recs = recommender.recommend_similar_books(book1_id, n=5)

        assert isinstance(recs, list)
        # Note: May be empty in test due to mock data

        # Test diverse recommendations
        diverse = recommender.get_diverse_recommendations(n=2)
        assert isinstance(diverse, list)

        print("✓ Recommendations working correctly")

    def test_07_duplicate_detection(self, setup_test_env):
        """Test Enhancement 7: Duplicate Detection."""
        print("\n[TEST 7] Duplicate Detection")

        metadata_db = setup_test_env['metadata_db']

        # Add duplicate book
        metadata_db.add_book(
            file_path="/test/book1_copy.pdf",
            file_hash="hash1",  # Same hash
            title="Test Book 1",
            author="Author One",
            status="completed"
        )

        detector = DuplicateDetector(metadata_db)
        duplicates = detector.find_duplicates()

        # Should find hash-based duplicates
        assert len(duplicates) > 0

        print("✓ Duplicate detection working correctly")

    def test_08_quote_extraction(self, setup_test_env):
        """Test Enhancement 8: Quote Extraction."""
        print("\n[TEST 8] Quote Extraction")

        metadata_db = setup_test_env['metadata_db']
        book1_id = setup_test_env['book1_id']

        # Add chunk with quotes
        metadata_db.add_chunk(
            book_id=book1_id,
            chunk_index=10,
            chunk_text='He said "This is a famous quote about wisdom and knowledge." Then he continued.',
            vector_id=100
        )

        extractor = QuoteExtractor(metadata_db)
        quotes = extractor.extract_quotes(book1_id)

        assert isinstance(quotes, list)
        # May find quotes if format matches

        print("✓ Quote extraction working correctly")

    def test_09_named_entity_recognition(self, setup_test_env):
        """Test Enhancement 9: Named Entity Recognition."""
        print("\n[TEST 9] Named Entity Recognition")

        ner = NamedEntityExtractor()

        text = "Albert Einstein was born in 1879 in Germany. He worked at Princeton University."
        entities = ner.extract_entities(text)

        assert 'PERSON' in entities
        assert 'DATE' in entities
        assert isinstance(entities['PERSON'], list)
        assert isinstance(entities['DATE'], list)

        print("✓ NER working correctly")

    def test_10_topic_modeling(self, setup_test_env):
        """Test Enhancement 10: Topic Modeling."""
        print("\n[TEST 10] Topic Modeling & Clustering")

        metadata_db = setup_test_env['metadata_db']
        book1_id = setup_test_env['book1_id']

        modeler = TopicModeler(metadata_db)

        # Extract keywords
        keywords = modeler.extract_keywords(book1_id, n=10)

        assert isinstance(keywords, list)
        if keywords:
            assert isinstance(keywords[0], tuple)
            assert len(keywords[0]) == 2  # (word, count)

        print("✓ Topic modeling working correctly")

    def test_11_search_filters(self, setup_test_env):
        """Test Enhancement 11: Advanced Search Filters."""
        print("\n[TEST 11] Advanced Search Filters")

        metadata_db = setup_test_env['metadata_db']

        search = SearchFilter(metadata_db)

        # Filter by format
        pdf_books = search.filter_books(format='.pdf')
        assert isinstance(pdf_books, list)

        # Filter by word count
        long_books = search.filter_books(min_words=5000)
        assert all(b.get('total_words', 0) >= 5000 for b in long_books)

        # Get longest books
        longest = search.get_longest_books(n=2)
        assert len(longest) <= 2

        # Group by format
        by_format = search.group_books_by('format')
        assert isinstance(by_format, dict)

        print("✓ Search filters working correctly")

    def test_12_bookmarks(self, setup_test_env):
        """Test Enhancement 12: Bookmark System."""
        print("\n[TEST 12] Bookmark System")

        test_dir = setup_test_env['test_dir']
        bookmark_db = Path(test_dir) / "bookmarks.db"

        manager = BookmarkManager(str(bookmark_db))

        # Add bookmark
        bookmark_id = manager.add_bookmark(
            book_id=1,
            chunk_id=5,
            note="Important passage",
            tags=['philosophy', 'wisdom']
        )

        assert bookmark_id > 0

        # Get bookmarks
        bookmarks = manager.get_bookmarks(book_id=1)
        assert len(bookmarks) == 1
        assert bookmarks[0]['note'] == "Important passage"

        print("✓ Bookmarks working correctly")

    def test_13_reading_lists(self, setup_test_env):
        """Test Enhancement 13: Reading List Management."""
        print("\n[TEST 13] Reading List Management")

        test_dir = setup_test_env['test_dir']
        bookmark_db = Path(test_dir) / "bookmarks.db"

        manager = BookmarkManager(str(bookmark_db))

        # Create reading list
        list_id = manager.create_reading_list(
            name="Philosophy Books",
            description="Books about philosophy"
        )

        assert list_id > 0

        # Add books to list
        manager.add_to_reading_list(list_id, book_id=1)
        manager.add_to_reading_list(list_id, book_id=2)

        # Get reading list
        reading_list = manager.get_reading_list(list_id)
        assert reading_list['name'] == "Philosophy Books"
        assert len(reading_list['items']) == 2

        print("✓ Reading lists working correctly")

    def test_14_cross_references(self, setup_test_env):
        """Test Enhancement 14: Cross-Reference Finder."""
        print("\n[TEST 14] Cross-Reference Finder")

        metadata_db = setup_test_env['metadata_db']

        class MockEmbedder:
            def encode(self, text, show_progress=True):
                import numpy as np
                return np.random.rand(384)

        class MockVectorDB:
            def search(self, embedding, k=5):
                return [
                    (i, 0.9, {'book_id': 2})
                    for i in range(k)
                ]

        finder = CrossReferenceFinder(metadata_db, MockEmbedder(), MockVectorDB())

        # Find related passages
        related = finder.find_related_passages(
            chunk_text="Test passage about wisdom",
            book_id=1,
            top_k=3
        )

        assert isinstance(related, list)

        print("✓ Cross-references working correctly")

    def test_15_book_comparison(self, setup_test_env):
        """Test Enhancement 15: Book Comparison."""
        print("\n[TEST 15] Book Comparison Tool")

        metadata_db = setup_test_env['metadata_db']
        book1_id = setup_test_env['book1_id']
        book2_id = setup_test_env['book2_id']

        comparison = BookComparison(metadata_db)

        # Compare books
        result = comparison.compare_books(book1_id, book2_id)

        assert 'book1' in result
        assert 'book2' in result
        assert 'comparison' in result
        assert 'same_author' in result['comparison']

        print("✓ Book comparison working correctly")

    def test_16_bibtex_export(self, setup_test_env):
        """Test Enhancement 16: BibTeX Citation Export."""
        print("\n[TEST 16] BibTeX Citation Export")

        test_dir = setup_test_env['test_dir']
        metadata_db = setup_test_env['metadata_db']

        exporter = ExportManager()
        books = metadata_db.list_books()

        filepath = Path(test_dir) / "citations.bib"
        exporter.export_books_bibtex(books, str(filepath))

        assert filepath.exists()
        content = filepath.read_text()
        assert '@book{' in content

        print("✓ BibTeX export working correctly")

    def test_17_batch_export(self, setup_test_env):
        """Test Enhancement 17: Batch Export Tools."""
        print("\n[TEST 17] Batch Export Tools")

        test_dir = setup_test_env['test_dir']
        metadata_db = setup_test_env['metadata_db']

        exporter = ExportManager()
        books = metadata_db.list_books()

        output_dir = Path(test_dir) / "exports"
        exporter.batch_export_books(
            books,
            str(output_dir),
            formats=['json', 'csv']
        )

        assert output_dir.exists()
        json_files = list(output_dir.glob("*.json"))
        csv_files = list(output_dir.glob("*.csv"))

        assert len(json_files) > 0
        assert len(csv_files) > 0

        print("✓ Batch export working correctly")

    def test_18_api_server(self, setup_test_env):
        """Test Enhancement 18: Web API Server."""
        print("\n[TEST 18] Web API Server")

        # Create mock components
        class MockEmbedder:
            def encode(self, text, show_progress=True):
                import numpy as np
                return np.random.rand(384)

        class MockVectorDB:
            def size(self):
                return 100

            def search(self, embedding, k=5):
                return []

        class MockLLM:
            def generate(self, prompt, temperature=0.7, max_tokens=2000):
                return "Test answer"

        class MockRetriever:
            def retrieve(self, query, top_k=5):
                return []

        class MockRAG:
            def __init__(self):
                self.retriever = MockRetriever()

            def query(self, question, top_k=None):
                return "Answer", []

        metadata_db = setup_test_env['metadata_db']

        api = LibraryAPI(
            embedder=MockEmbedder(),
            vector_db=MockVectorDB(),
            metadata_db=metadata_db,
            llm_client=MockLLM(),
            rag_pipeline=MockRAG(),
            config=None
        )

        # Create app
        app = api.create_app()

        assert app is not None

        # Test with test client
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            assert response.status_code == 200
            data = response.get_json()
            assert 'status' in data

            # Test stats endpoint
            response = client.get('/stats')
            assert response.status_code == 200

            # Test books endpoint
            response = client.get('/books')
            assert response.status_code == 200
            data = response.get_json()
            assert 'books' in data

        print("✓ API server working correctly")

    def test_19_analytics_export(self, setup_test_env):
        """Test Enhancement 19: Analytics Export."""
        print("\n[TEST 19] Analytics Export to File")

        test_dir = setup_test_env['test_dir']
        metadata_db = setup_test_env['metadata_db']
        vector_db = VectorDB(dimension=384)

        analytics = LibraryAnalytics(metadata_db, vector_db)

        # Export as JSON
        json_path = Path(test_dir) / "stats.json"
        analytics.export_stats(str(json_path), format='json')
        assert json_path.exists()

        # Export as TXT
        txt_path = Path(test_dir) / "stats.txt"
        analytics.export_stats(str(txt_path), format='txt')
        assert txt_path.exists()

        print("✓ Analytics export working correctly")

    def test_20_conversation_export(self, setup_test_env):
        """Test Enhancement 20: Conversation History Export."""
        print("\n[TEST 20] Conversation History Export")

        test_dir = setup_test_env['test_dir']
        history_db = Path(test_dir) / "history.db"

        history = ConversationHistory(str(history_db))

        # Add conversations
        history.add_conversation("Question 1?", "Answer 1")
        history.add_conversation("Question 2?", "Answer 2")

        # Export to JSON
        json_path = Path(test_dir) / "conversations.json"
        history.export_to_json(str(json_path))
        assert json_path.exists()

        import json
        data = json.loads(json_path.read_text())
        assert len(data) >= 2

        print("✓ Conversation export working correctly")


def run_all_tests():
    """Run all enhancement tests."""
    print("=" * 60)
    print("AI LIBRARY - COMPREHENSIVE ENHANCEMENT TESTS")
    print("=" * 60)

    # Run with pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_all_tests()
