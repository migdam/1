#!/usr/bin/env python3
"""RAG-based query interface for the AI Library."""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_loader import get_config
from logger import setup_logger
from metadata_db import MetadataDB
from embedder import create_embedder
from vector_db import VectorDB
from llm_client import create_llm_from_config
from retriever import create_rag_pipeline

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class QueryInterface:
    """Interactive query interface."""

    def __init__(self, rag_pipeline, config, logger):
        """Initialize query interface.

        Args:
            rag_pipeline: RAG pipeline instance
            config: Configuration object
            logger: Logger instance
        """
        self.rag_pipeline = rag_pipeline
        self.config = config
        self.logger = logger

        if HAS_RICH:
            self.console = Console()
        else:
            self.console = None

    def print(self, message: str, style: str = None) -> None:
        """Print a message.

        Args:
            message: Message to print
            style: Optional rich style
        """
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_panel(self, message: str, title: str = None) -> None:
        """Print a panel.

        Args:
            message: Panel content
            title: Panel title
        """
        if self.console:
            self.console.print(Panel(message, title=title))
        else:
            if title:
                print(f"\n=== {title} ===")
            print(message)
            print()

    def query_single(self, question: str, show_sources: bool = True) -> None:
        """Process a single query.

        Args:
            question: User question
            show_sources: Whether to show source documents
        """
        self.print(f"\n[bold cyan]Question:[/bold cyan] {question}", style="cyan")
        self.print("\n[yellow]Searching knowledge base...[/yellow]")

        try:
            # Get answer
            answer, results = self.rag_pipeline.query(
                question,
                top_k=self.config.top_k,
                max_context_length=self.config.get('rag.max_context_length')
            )

            # Display answer
            self.print("\n[bold green]Answer:[/bold green]")
            if self.console:
                self.console.print(Markdown(answer))
            else:
                print(answer)

            # Display sources
            if show_sources and results:
                self.print("\n[bold blue]Sources:[/bold blue]")

                if self.console:
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("#", style="dim", width=3)
                    table.add_column("Book", style="cyan")
                    table.add_column("Author", style="yellow")
                    table.add_column("Score", justify="right", style="green")
                    table.add_column("Preview")

                    for i, result in enumerate(results, 1):
                        preview = result.chunk_text[:100] + "..." if len(result.chunk_text) > 100 else result.chunk_text
                        table.add_row(
                            str(i),
                            result.book_title,
                            result.book_author,
                            f"{result.similarity_score:.4f}",
                            preview
                        )

                    self.console.print(table)
                else:
                    for i, result in enumerate(results, 1):
                        print(f"\n[{i}] {result.book_title} by {result.book_author}")
                        print(f"    Score: {result.similarity_score:.4f}")
                        print(f"    Preview: {result.chunk_text[:150]}...")

        except Exception as e:
            self.logger.error(f"Error processing query: {str(e)}")
            self.print(f"\n[bold red]Error:[/bold red] {str(e)}", style="red")

    def interactive_mode(self) -> None:
        """Run interactive query mode."""
        self.print_panel(
            "AI Library RAG Query Interface\n\n"
            "Ask questions about your book collection.\n"
            "Commands:\n"
            "  - Type your question and press Enter\n"
            "  - 'quit' or 'exit' to exit\n"
            "  - 'help' for help",
            title="Welcome"
        )

        while True:
            try:
                if self.console:
                    question = self.console.input("\n[bold green]❯[/bold green] ")
                else:
                    question = input("\n❯ ")

                question = question.strip()

                if not question:
                    continue

                if question.lower() in ['quit', 'exit', 'q']:
                    self.print("\n[yellow]Goodbye![/yellow]")
                    break

                if question.lower() == 'help':
                    self.print_panel(
                        "Available commands:\n"
                        "  - Type any question to search your library\n"
                        "  - 'quit' or 'exit' - Exit the program\n"
                        "  - 'help' - Show this help message\n\n"
                        f"Current settings:\n"
                        f"  - LLM Provider: {self.config.llm_provider}\n"
                        f"  - Top-K Results: {self.config.top_k}\n"
                        f"  - Embedding Model: {self.config.embedding_model}",
                        title="Help"
                    )
                    continue

                # Process query
                self.query_single(question, show_sources=True)

            except KeyboardInterrupt:
                self.print("\n\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
                continue
            except EOFError:
                self.print("\n[yellow]Goodbye![/yellow]")
                break


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Query the AI Library using RAG"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--query',
        '-q',
        type=str,
        help='Single query mode (non-interactive)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        help='Override top-k results'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['openai', 'gemini', 'claude', 'local'],
        help='Override LLM provider'
    )
    parser.add_argument(
        '--no-sources',
        action='store_true',
        help='Don\'t show source documents'
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(args.config)

    # Setup logger
    logger = setup_logger(
        name="rag_query",
        log_file=str(config.logs_path / "rag_query.log"),
        level=config.get('logging.level', 'INFO'),
        console=False  # Don't log to console in interactive mode
    )

    # Override config if specified
    if args.top_k:
        config.set('rag.top_k', args.top_k)

    if args.provider:
        config.set('llm.provider', args.provider)

    # Check if vector DB exists
    vector_db_path = config.vector_db_path
    if not vector_db_path.with_suffix('.index').exists():
        print(f"Error: Vector database not found at {vector_db_path}")
        print("Please run build_vector_base.py first to process your books.")
        return 1

    # Check if metadata DB exists
    metadata_db_path = config.metadata_db_path
    if not metadata_db_path.exists():
        print(f"Error: Metadata database not found at {metadata_db_path}")
        print("Please run build_vector_base.py first to process your books.")
        return 1

    print("Loading AI Library...")
    print(f"LLM Provider: {config.llm_provider}")
    print(f"Embedding Model: {config.embedding_model}")

    # Load components
    try:
        # Metadata DB
        logger.info("Loading metadata database...")
        metadata_db = MetadataDB(str(metadata_db_path))

        # Embedder
        logger.info("Loading embedding model...")
        embedder = create_embedder(
            model_name=config.embedding_model,
            device=config.embedding_device,
            batch_size=config.embedding_batch_size,
            cache_dir=config.get('embedding.cache_dir'),
            logger=logger
        )

        # Vector DB
        logger.info("Loading vector database...")
        vector_db = VectorDB.load(str(vector_db_path), logger=logger)

        print(f"Loaded {vector_db.size()} document chunks from {metadata_db.get_stats()['total_books']} books")

        # LLM Client
        logger.info("Initializing LLM client...")
        llm_client = create_llm_from_config(config, logger=logger)

        # RAG Pipeline
        logger.info("Creating RAG pipeline...")
        rag_pipeline = create_rag_pipeline(
            embedder=embedder,
            vector_db=vector_db,
            metadata_db=metadata_db,
            llm_client=llm_client,
            config=config,
            logger=logger
        )

        print("AI Library loaded successfully!\n")

    except Exception as e:
        print(f"Error loading AI Library: {str(e)}")
        logger.error(f"Error loading components: {str(e)}")
        return 1

    # Create query interface
    interface = QueryInterface(rag_pipeline, config, logger)

    # Single query or interactive mode
    if args.query:
        interface.query_single(args.query, show_sources=not args.no_sources)
    else:
        interface.interactive_mode()

    return 0


if __name__ == '__main__':
    sys.exit(main())
