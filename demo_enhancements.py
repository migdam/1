#!/usr/bin/env python3
"""Demo script showcasing all 20 enhancements."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


def print_section(title: str):
    """Print section header."""
    console.print(f"\n{'='*60}")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"{'='*60}\n")


def demo_enhancement_01():
    """Demo 1: Analytics & Statistics Dashboard."""
    print_section("ENHANCEMENT 1: Analytics & Statistics Dashboard")

    from src.metadata_db import MetadataDB
    from src.vector_db import VectorDB
    from src.analytics import LibraryAnalytics

    # Check if database exists
    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found. Run build_vector_base.py first.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))
    vector_db_path = Path("./data/books_index")

    if not vector_db_path.with_suffix('.index').exists():
        console.print("[yellow]No vector database found.[/yellow]")
        return

    vector_db = VectorDB.load(str(vector_db_path))

    # Create analytics
    analytics = LibraryAnalytics(metadata_db, vector_db)

    # Get statistics
    stats = analytics.get_comprehensive_stats()

    # Display overview
    table = Table(title="Library Overview")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    overview = stats['overview']
    table.add_row("Total Books", str(overview['total_books']))
    table.add_row("Total Chunks", str(overview['total_chunks']))
    table.add_row("Total Words", f"{overview['total_words']:,}")
    table.add_row("Total Vectors", str(overview['total_vectors']))
    table.add_row("Avg Chunks/Book", f"{overview['avg_chunks_per_book']:.1f}")

    console.print(table)

    # Show report
    console.print("\n[bold]Full Analytics Report:[/bold]")
    report = analytics.generate_report()
    console.print(Panel(report[:500] + "...", title="Analytics Report"))


def demo_enhancement_02_03_04():
    """Demo 2-4: Export Functionality (Markdown, JSON, CSV)."""
    print_section("ENHANCEMENTS 2-4: Export Tools (Markdown, JSON, CSV)")

    from src.export_tools import ExportManager
    from src.metadata_db import MetadataDB

    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))
    exporter = ExportManager()

    # Get books
    books = metadata_db.list_books(limit=5)

    if not books:
        console.print("[yellow]No books found.[/yellow]")
        return

    # Export to different formats
    output_dir = Path("./exports_demo")
    output_dir.mkdir(exist_ok=True)

    # JSON export
    import json
    json_path = output_dir / "books.json"
    with open(json_path, 'w') as f:
        json.dump(books, f, indent=2)
    console.print(f"✓ Exported to JSON: {json_path}")

    # CSV export
    csv_path = output_dir / "books.csv"
    exporter.export_books_csv(books, str(csv_path))
    console.print(f"✓ Exported to CSV: {csv_path}")

    # BibTeX export
    bib_path = output_dir / "citations.bib"
    exporter.export_books_bibtex(books, str(bib_path))
    console.print(f"✓ Exported to BibTeX: {bib_path}")

    console.print(f"\n[green]All exports saved to {output_dir}/[/green]")


def demo_enhancement_05():
    """Demo 5: Conversation History."""
    print_section("ENHANCEMENT 5: Conversation History Tracking")

    from src.conversation_history import ConversationHistory

    history = ConversationHistory("./data/conversation_history.db")

    # Add sample conversation
    history.add_conversation(
        question="What is the meaning of life?",
        answer="The meaning of life is a philosophical question...",
        session_id="demo_session",
        llm_provider="local"
    )

    # Get recent conversations
    recent = history.get_recent_conversations(limit=5)

    table = Table(title="Recent Conversations")
    table.add_column("ID", style="cyan")
    table.add_column("Question", style="yellow")
    table.add_column("Sources", style="green")
    table.add_column("Time", style="magenta")

    for conv in recent[:5]:
        table.add_row(
            str(conv['id']),
            conv['question'][:50] + "...",
            str(conv['source_count']),
            conv['timestamp'][:19]
        )

    console.print(table)

    # Get statistics
    stats = history.get_statistics()
    console.print(f"\n[cyan]Total Conversations:[/cyan] {stats['total_conversations']}")


def demo_enhancement_06():
    """Demo 6: Book Recommendations."""
    print_section("ENHANCEMENT 6: Book Recommendation System")

    from src.recommendations import BookRecommender
    from src.metadata_db import MetadataDB
    from src.embedder import create_embedder
    from src.vector_db import VectorDB

    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))

    try:
        embedder = create_embedder(model_name="intfloat/e5-small-v2", device="cpu")
        vector_db = VectorDB.load("./data/books_index")

        recommender = BookRecommender(embedder, vector_db, metadata_db)

        # Get diverse recommendations
        recs = recommender.get_diverse_recommendations(n=5)

        if recs:
            table = Table(title="Recommended Books")
            table.add_column("Title", style="cyan")
            table.add_column("Author", style="yellow")
            table.add_column("Words", style="green")
            table.add_column("Language", style="magenta")

            for rec in recs:
                table.add_row(
                    rec['title'][:40],
                    rec['author'][:30],
                    f"{rec.get('word_count', 0):,}",
                    rec.get('language', 'unknown')
                )

            console.print(table)
        else:
            console.print("[yellow]No recommendations available.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


def demo_enhancement_07():
    """Demo 7: Duplicate Detection."""
    print_section("ENHANCEMENT 7: Duplicate Detection")

    from src.advanced_features import DuplicateDetector
    from src.metadata_db import MetadataDB

    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))
    detector = DuplicateDetector(metadata_db)

    duplicates = detector.find_duplicates()

    if duplicates:
        console.print(f"[yellow]Found {len(duplicates)} duplicate groups:[/yellow]")
        for i, group in enumerate(duplicates, 1):
            console.print(f"\nGroup {i}:")
            for book in group:
                console.print(f"  - {book.get('title', 'Unknown')} ({book.get('file_path', '')})")
    else:
        console.print("[green]No duplicates found![/green]")


def demo_enhancement_08():
    """Demo 8: Quote Extraction."""
    print_section("ENHANCEMENT 8: Quote Extraction")

    from src.advanced_features import QuoteExtractor
    from src.metadata_db import MetadataDB

    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))
    extractor = QuoteExtractor(metadata_db)

    # Get first book
    books = metadata_db.list_books(limit=1)
    if not books:
        console.print("[yellow]No books found.[/yellow]")
        return

    book = books[0]
    quotes = extractor.extract_quotes(book['id'], min_length=50, max_length=300)

    if quotes:
        console.print(f"[cyan]Found {len(quotes)} quotes in '{book.get('title', 'Unknown')}':[/cyan]\n")
        for i, quote in enumerate(quotes[:3], 1):
            console.print(Panel(quote['text'], title=f"Quote {i}"))
    else:
        console.print("[yellow]No quotes found in this book.[/yellow]")


def demo_enhancement_09():
    """Demo 9: Named Entity Recognition."""
    print_section("ENHANCEMENT 9: Named Entity Recognition")

    from src.advanced_features import NamedEntityExtractor

    ner = NamedEntityExtractor()

    sample_text = """
    Albert Einstein was born in Germany in 1879. He later worked at
    Princeton University in New Jersey. His theory of relativity
    revolutionized physics in the 20th century.
    """

    entities = ner.extract_entities(sample_text)

    table = Table(title="Extracted Entities")
    table.add_column("Type", style="cyan")
    table.add_column("Entities", style="yellow")

    for entity_type, entity_list in entities.items():
        if entity_list:
            table.add_row(entity_type, ", ".join(entity_list[:5]))

    console.print(table)


def demo_enhancement_10():
    """Demo 10: Topic Modeling."""
    print_section("ENHANCEMENT 10: Topic Modeling & Keywords")

    from src.advanced_features import TopicModeler
    from src.metadata_db import MetadataDB

    db_path = Path("./data/books_metadata.db")
    if not db_path.exists():
        console.print("[yellow]No database found.[/yellow]")
        return

    metadata_db = MetadataDB(str(db_path))
    modeler = TopicModeler(metadata_db)

    # Get first book
    books = metadata_db.list_books(limit=1)
    if not books:
        console.print("[yellow]No books found.[/yellow]")
        return

    book = books[0]
    keywords = modeler.extract_keywords(book['id'], n=20)

    if keywords:
        table = Table(title=f"Top Keywords in '{book.get('title', 'Unknown')}'")
        table.add_column("Keyword", style="cyan")
        table.add_column("Frequency", style="green")

        for kw, freq in keywords[:15]:
            table.add_row(kw, str(freq))

        console.print(table)
    else:
        console.print("[yellow]No keywords extracted.[/yellow]")


def demo_all_enhancements():
    """Run all enhancement demos."""
    console.print(Panel.fit(
        "[bold cyan]AI LIBRARY - 20 ENHANCEMENTS DEMO[/bold cyan]",
        border_style="cyan"
    ))

    # Run each demo
    demos = [
        ("Analytics Dashboard", demo_enhancement_01),
        ("Export Tools", demo_enhancement_02_03_04),
        ("Conversation History", demo_enhancement_05),
        ("Book Recommendations", demo_enhancement_06),
        ("Duplicate Detection", demo_enhancement_07),
        ("Quote Extraction", demo_enhancement_08),
        ("Named Entity Recognition", demo_enhancement_09),
        ("Topic Modeling", demo_enhancement_10),
    ]

    for name, demo_func in demos:
        try:
            demo_func()
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error in {name}: {str(e)}[/red]")

        # Pause between demos
        if demo_func != demos[-1][1]:
            console.input("\n[dim]Press Enter to continue to next demo...[/dim]")

    console.print("\n" + "=" * 60)
    console.print("[bold green]Demo Complete![/bold green]")
    console.print("=" * 60)


if __name__ == '__main__':
    demo_all_enhancements()
