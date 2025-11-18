"""Metadata database for tracking processed books."""

import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager


class MetadataDB:
    """SQLite database for book metadata."""

    def __init__(self, db_path: str = "./data/books_metadata.db"):
        """Initialize metadata database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Books table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER,
                    format TEXT,
                    title TEXT,
                    author TEXT,
                    language TEXT,
                    detected_language TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    total_words INTEGER,
                    total_chars INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    extraction_time REAL,
                    embedding_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_hash TEXT NOT NULL,
                    word_count INTEGER,
                    char_count INTEGER,
                    start_pos INTEGER,
                    end_pos INTEGER,
                    vector_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
                    UNIQUE(book_id, chunk_index)
                )
            """)

            # Processing logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_books_hash
                ON books(file_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_books_status
                ON books(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_book_id
                ON chunks(book_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_vector_id
                ON chunks(vector_id)
            """)

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Compute SHA256 hash of text.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def add_book(
        self,
        file_path: str,
        file_hash: str = None,
        **metadata
    ) -> int:
        """Add a book to the database.

        Args:
            file_path: Path to book file
            file_hash: Optional pre-computed file hash
            **metadata: Additional metadata fields

        Returns:
            Book ID
        """
        file_path = Path(file_path)

        if file_hash is None:
            file_hash = self.compute_file_hash(file_path)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Prepare data
            data = {
                'file_path': str(file_path.absolute()),
                'file_hash': file_hash,
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'format': file_path.suffix.lower(),
                'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                if file_path.exists() else None,
                **metadata
            }

            # Build INSERT query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO books ({columns}) VALUES ({placeholders})"

            try:
                cursor.execute(query, list(data.values()))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Book already exists, return existing ID
                cursor.execute(
                    "SELECT id FROM books WHERE file_path = ?",
                    (str(file_path.absolute()),)
                )
                row = cursor.fetchone()
                return row['id'] if row else None

    def update_book(self, book_id: int, **metadata) -> None:
        """Update book metadata.

        Args:
            book_id: Book ID
            **metadata: Fields to update
        """
        if not metadata:
            return

        metadata['updated_at'] = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            set_clause = ', '.join([f"{k} = ?" for k in metadata.keys()])
            query = f"UPDATE books SET {set_clause} WHERE id = ?"

            cursor.execute(query, list(metadata.values()) + [book_id])

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get book by ID.

        Args:
            book_id: Book ID

        Returns:
            Book metadata dictionary or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_book_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get book by file path.

        Args:
            file_path: Path to book file

        Returns:
            Book metadata dictionary or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM books WHERE file_path = ?",
                (str(Path(file_path).absolute()),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_chunk(
        self,
        book_id: int,
        chunk_index: int,
        chunk_text: str,
        vector_id: int = None,
        **metadata
    ) -> int:
        """Add a chunk to the database.

        Args:
            book_id: Book ID
            chunk_index: Chunk index
            chunk_text: Chunk text
            vector_id: Vector database ID
            **metadata: Additional metadata

        Returns:
            Chunk ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            chunk_hash = self.compute_text_hash(chunk_text)

            data = {
                'book_id': book_id,
                'chunk_index': chunk_index,
                'chunk_text': chunk_text,
                'chunk_hash': chunk_hash,
                'word_count': len(chunk_text.split()),
                'char_count': len(chunk_text),
                'vector_id': vector_id,
                **metadata
            }

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO chunks ({columns}) VALUES ({placeholders})"

            cursor.execute(query, list(data.values()))
            return cursor.lastrowid

    def get_chunks(self, book_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a book.

        Args:
            book_id: Book ID

        Returns:
            List of chunk dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chunks WHERE book_id = ? ORDER BY chunk_index",
                (book_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_chunk_by_vector_id(self, vector_id: int) -> Optional[Dict[str, Any]]:
        """Get chunk by vector ID.

        Args:
            vector_id: Vector database ID

        Returns:
            Chunk dictionary or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chunks WHERE vector_id = ?",
                (vector_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def log_processing(
        self,
        operation: str,
        status: str,
        book_id: int = None,
        message: str = None,
        duration: float = None
    ) -> None:
        """Log a processing operation.

        Args:
            operation: Operation name
            status: Status (success, error, etc.)
            book_id: Optional book ID
            message: Optional message
            duration: Optional duration in seconds
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO processing_logs
                (book_id, operation, status, message, duration)
                VALUES (?, ?, ?, ?, ?)
                """,
                (book_id, operation, status, message, duration)
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total books
            cursor.execute("SELECT COUNT(*) as count FROM books")
            stats['total_books'] = cursor.fetchone()['count']

            # Books by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM books
                GROUP BY status
            """)
            stats['books_by_status'] = {
                row['status']: row['count']
                for row in cursor.fetchall()
            }

            # Total chunks
            cursor.execute("SELECT COUNT(*) as count FROM chunks")
            stats['total_chunks'] = cursor.fetchone()['count']

            # Total words
            cursor.execute("SELECT SUM(total_words) as total FROM books")
            stats['total_words'] = cursor.fetchone()['total'] or 0

            # Books by format
            cursor.execute("""
                SELECT format, COUNT(*) as count
                FROM books
                GROUP BY format
            """)
            stats['books_by_format'] = {
                row['format']: row['count']
                for row in cursor.fetchall()
            }

            # Average processing time
            cursor.execute("""
                SELECT AVG(extraction_time) as avg_extraction,
                       AVG(embedding_time) as avg_embedding
                FROM books
                WHERE extraction_time IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['avg_extraction_time'] = row['avg_extraction'] or 0
            stats['avg_embedding_time'] = row['avg_embedding'] or 0

            return stats

    def list_books(
        self,
        status: str = None,
        limit: int = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List books with optional filtering.

        Args:
            status: Optional status filter
            limit: Optional result limit
            offset: Optional result offset

        Returns:
            List of book dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM books"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close database (not needed with context manager, but provided for compatibility)."""
        pass
