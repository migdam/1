"""Export utilities for AI Library results and data."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class ExportManager:
    """Manager for exporting library data in various formats."""

    def __init__(self, logger=None):
        """Initialize export manager.

        Args:
            logger: Optional logger
        """
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def export_results_markdown(
        self,
        question: str,
        answer: str,
        results: List,
        filepath: str
    ) -> None:
        """Export RAG results to Markdown.

        Args:
            question: User question
            answer: LLM answer
            results: List of RetrievalResult objects
            filepath: Output file path
        """
        md_lines = []

        # Header
        md_lines.append(f"# AI Library Query Result\n")
        md_lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_lines.append("---\n")

        # Question
        md_lines.append(f"## Question\n")
        md_lines.append(f"{question}\n")

        # Answer
        md_lines.append(f"## Answer\n")
        md_lines.append(f"{answer}\n")

        # Sources
        md_lines.append(f"## Sources\n")
        for i, result in enumerate(results, 1):
            md_lines.append(f"### [{i}] {result.book_title}")
            md_lines.append(f"**Author**: {result.book_author}")
            md_lines.append(f"**Similarity Score**: {result.similarity_score:.4f}")
            md_lines.append(f"**Chunk Index**: {result.chunk_index}\n")
            md_lines.append(f"**Excerpt**:")
            md_lines.append(f"> {result.chunk_text}\n")

        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        self._log('info', f"Exported results to {filepath}")

    def export_results_json(
        self,
        question: str,
        answer: str,
        results: List,
        filepath: str
    ) -> None:
        """Export RAG results to JSON.

        Args:
            question: User question
            answer: LLM answer
            results: List of RetrievalResult objects
            filepath: Output file path
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'sources': [
                {
                    'book_title': r.book_title,
                    'book_author': r.book_author,
                    'similarity_score': r.similarity_score,
                    'chunk_index': r.chunk_index,
                    'chunk_text': r.chunk_text,
                    'book_id': r.book_id,
                }
                for r in results
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self._log('info', f"Exported results to {filepath}")

    def export_books_csv(
        self,
        books: List[Dict[str, Any]],
        filepath: str
    ) -> None:
        """Export book list to CSV.

        Args:
            books: List of book dictionaries
            filepath: Output file path
        """
        if not books:
            self._log('warning', "No books to export")
            return

        # Define columns
        columns = [
            'id', 'title', 'author', 'format', 'file_path',
            'chunk_count', 'total_words', 'total_chars',
            'detected_language', 'status', 'created_at'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(books)

        self._log('info', f"Exported {len(books)} books to {filepath}")

    def export_books_bibtex(
        self,
        books: List[Dict[str, Any]],
        filepath: str
    ) -> None:
        """Export books as BibTeX citations.

        Args:
            books: List of book dictionaries
            filepath: Output file path
        """
        bibtex_entries = []

        for book in books:
            title = book.get('title', 'Unknown')
            author = book.get('author', 'Unknown')
            year = self._extract_year(book.get('created_at', ''))

            # Create citation key
            author_key = author.split()[0] if author != 'Unknown' else 'Unknown'
            cite_key = f"{author_key}{year}"

            entry = f"""@book{{{cite_key},
    title = {{{title}}},
    author = {{{author}}},
    year = {{{year}}},
    note = {{Processed by AI Library}}
}}
"""
            bibtex_entries.append(entry)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bibtex_entries))

        self._log('info', f"Exported {len(books)} books to BibTeX: {filepath}")

    def export_conversation_history(
        self,
        history: List[Dict[str, Any]],
        filepath: str,
        format: str = 'json'
    ) -> None:
        """Export conversation history.

        Args:
            history: List of conversation entries
            filepath: Output file path
            format: Export format (json, markdown)
        """
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        elif format == 'markdown':
            md_lines = []
            md_lines.append("# AI Library Conversation History\n")

            for entry in history:
                md_lines.append(f"## {entry['timestamp']}\n")
                md_lines.append(f"**Q**: {entry['question']}\n")
                md_lines.append(f"**A**: {entry['answer']}\n")
                md_lines.append("---\n")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))

        self._log('info', f"Exported conversation history to {filepath}")

    def export_quotes(
        self,
        quotes: List[Dict[str, Any]],
        filepath: str,
        format: str = 'markdown'
    ) -> None:
        """Export extracted quotes.

        Args:
            quotes: List of quote dictionaries
            filepath: Output file path
            format: Export format (markdown, json, txt)
        """
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(quotes, f, indent=2, ensure_ascii=False)

        elif format == 'markdown':
            md_lines = []
            md_lines.append("# Extracted Quotes\n")

            for quote in quotes:
                md_lines.append(f"## {quote['book_title']}\n")
                md_lines.append(f"*by {quote['book_author']}*\n")
                md_lines.append(f"> {quote['text']}\n")
                md_lines.append("---\n")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))

        elif format == 'txt':
            lines = []
            for quote in quotes:
                lines.append(f"{quote['text']}")
                lines.append(f"  — {quote['book_author']}, {quote['book_title']}")
                lines.append("")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        self._log('info', f"Exported {len(quotes)} quotes to {filepath}")

    def batch_export_books(
        self,
        books: List[Dict[str, Any]],
        output_dir: str,
        formats: List[str] = ['json', 'csv', 'bibtex']
    ) -> None:
        """Export books in multiple formats.

        Args:
            books: List of book dictionaries
            output_dir: Output directory
            formats: List of formats to export
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if 'json' in formats:
            filepath = output_path / f"books_{timestamp}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(books, f, indent=2, ensure_ascii=False)

        if 'csv' in formats:
            filepath = output_path / f"books_{timestamp}.csv"
            self.export_books_csv(books, str(filepath))

        if 'bibtex' in formats:
            filepath = output_path / f"books_{timestamp}.bib"
            self.export_books_bibtex(books, str(filepath))

        self._log('info', f"Batch exported books to {output_dir}")

    @staticmethod
    def _extract_year(date_str: str) -> str:
        """Extract year from ISO date string."""
        if not date_str:
            return str(datetime.now().year)
        return date_str.split('-')[0] if '-' in date_str else str(datetime.now().year)
