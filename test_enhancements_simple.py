#!/usr/bin/env python3
"""Simple test script for enhancements (no pytest required)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_imports():
    """Test that all enhancement modules can be imported."""
    print("Testing module imports...")

    modules = [
        ('Analytics', 'src.analytics', 'LibraryAnalytics'),
        ('Export Tools', 'src.export_tools', 'ExportManager'),
        ('Conversation History', 'src.conversation_history', 'ConversationHistory'),
        ('Recommendations', 'src.recommendations', 'BookRecommender'),
        ('Advanced Features', 'src.advanced_features', 'DuplicateDetector'),
        ('Advanced Features', 'src.advanced_features', 'QuoteExtractor'),
        ('Advanced Features', 'src.advanced_features', 'NamedEntityExtractor'),
        ('Advanced Features', 'src.advanced_features', 'TopicModeler'),
        ('Advanced Features', 'src.advanced_features', 'BookmarkManager'),
        ('Search Filters', 'src.search_filters', 'SearchFilter'),
        ('Search Filters', 'src.search_filters', 'CrossReferenceFinder'),
        ('Search Filters', 'src.search_filters', 'BookComparison'),
        ('API Server', 'src.api_server', 'LibraryAPI'),
    ]

    passed = 0
    failed = 0

    for name, module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✓ {name} ({class_name})")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name} ({class_name}): {str(e)}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_basic_functionality():
    """Test basic functionality of key features."""
    print("\n" + "="*60)
    print("Testing Basic Functionality")
    print("="*60)

    # Test 1: Analytics
    print("\n[TEST 1] Analytics")
    try:
        from src.analytics import LibraryAnalytics
        from src.metadata_db import MetadataDB
        from src.vector_db import VectorDB

        # Create in-memory test database
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        metadata_db = MetadataDB(path)
        vector_db = VectorDB(dimension=384)

        analytics = LibraryAnalytics(metadata_db, vector_db)
        stats = analytics.get_comprehensive_stats()

        assert 'overview' in stats
        assert 'books' in stats
        print("  ✓ Analytics working")

        os.unlink(path)
    except Exception as e:
        print(f"  ✗ Analytics failed: {e}")

    # Test 2: Export Manager
    print("\n[TEST 2] Export Manager")
    try:
        from src.export_tools import ExportManager

        exporter = ExportManager()
        print("  ✓ Export Manager initialized")
    except Exception as e:
        print(f"  ✗ Export Manager failed: {e}")

    # Test 3: Conversation History
    print("\n[TEST 3] Conversation History")
    try:
        from src.conversation_history import ConversationHistory

        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        history = ConversationHistory(path)
        conv_id = history.add_conversation("Test?", "Answer")

        assert conv_id > 0
        print("  ✓ Conversation History working")

        os.unlink(path)
    except Exception as e:
        print(f"  ✗ Conversation History failed: {e}")

    # Test 4: Named Entity Recognition
    print("\n[TEST 4] Named Entity Recognition")
    try:
        from src.advanced_features import NamedEntityExtractor

        ner = NamedEntityExtractor()
        entities = ner.extract_entities("Albert Einstein was born in 1879.")

        assert 'PERSON' in entities
        assert 'DATE' in entities
        print("  ✓ NER working")
    except Exception as e:
        print(f"  ✗ NER failed: {e}")

    # Test 5: Search Filters
    print("\n[TEST 5] Search Filters")
    try:
        from src.search_filters import SearchFilter
        from src.metadata_db import MetadataDB

        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        metadata_db = MetadataDB(path)
        search = SearchFilter(metadata_db)

        # Test filtering (should return empty list)
        results = search.filter_books(format='.pdf')
        print("  ✓ Search Filters working")

        os.unlink(path)
    except Exception as e:
        print(f"  ✗ Search Filters failed: {e}")

    # Test 6: Bookmark Manager
    print("\n[TEST 6] Bookmark Manager")
    try:
        from src.advanced_features import BookmarkManager

        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        manager = BookmarkManager(path)
        bookmark_id = manager.add_bookmark(book_id=1, note="Test note")

        assert bookmark_id > 0
        print("  ✓ Bookmark Manager working")

        os.unlink(path)
    except Exception as e:
        print(f"  ✗ Bookmark Manager failed: {e}")

    # Test 7: API Server
    print("\n[TEST 7] API Server")
    try:
        from src.api_server import LibraryAPI

        # Create mock objects
        class Mock:
            def size(self): return 0
            def get_stats(self): return {'total_books': 0}
            def list_books(self, **kwargs): return []

        api = LibraryAPI(
            embedder=Mock(),
            vector_db=Mock(),
            metadata_db=Mock(),
            llm_client=Mock(),
            rag_pipeline=Mock(),
            config=None
        )

        print("  ✓ API Server initialized")
    except ImportError as e:
        print(f"  ⚠ API Server requires Flask (optional): {e}")
    except Exception as e:
        print(f"  ✗ API Server failed: {e}")


def main():
    """Run all tests."""
    print("="*60)
    print("AI LIBRARY - ENHANCEMENT TESTS")
    print("="*60)

    # Test imports
    if not test_imports():
        print("\n⚠ Some imports failed")

    # Test functionality
    test_basic_functionality()

    print("\n" + "="*60)
    print("Tests Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
