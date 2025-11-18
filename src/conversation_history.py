"""Conversation history tracking for AI Library."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3


class ConversationHistory:
    """Track and manage conversation history."""

    def __init__(self, db_path: str = "./data/conversation_history.db", logger=None):
        """Initialize conversation history.

        Args:
            db_path: Path to SQLite database
            logger: Optional logger
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._init_db()

    def _log(self, level: str, message: str) -> None:
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source_count INTEGER,
                    top_score REAL,
                    llm_provider TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    book_id INTEGER,
                    book_title TEXT,
                    book_author TEXT,
                    chunk_index INTEGER,
                    similarity_score REAL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_session
                ON conversations(session_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_timestamp
                ON conversations(timestamp)
            """)

    def add_conversation(
        self,
        question: str,
        answer: str,
        results: List = None,
        session_id: str = None,
        llm_provider: str = None,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Add a conversation to history.

        Args:
            question: User question
            answer: LLM answer
            results: List of RetrievalResult objects
            session_id: Optional session identifier
            llm_provider: LLM provider used
            metadata: Additional metadata

        Returns:
            Conversation ID
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Insert conversation
            cursor.execute("""
                INSERT INTO conversations
                (session_id, question, answer, source_count, top_score, llm_provider, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                question,
                answer,
                len(results) if results else 0,
                results[0].similarity_score if results else None,
                llm_provider,
                json.dumps(metadata) if metadata else None
            ))

            conv_id = cursor.lastrowid

            # Insert sources
            if results:
                for result in results:
                    cursor.execute("""
                        INSERT INTO conversation_sources
                        (conversation_id, book_id, book_title, book_author,
                         chunk_index, similarity_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        conv_id,
                        result.book_id,
                        result.book_title,
                        result.book_author,
                        result.chunk_index,
                        result.similarity_score
                    ))

            conn.commit()

        self._log('debug', f"Added conversation {conv_id} to history")
        return conv_id

    def get_conversation(self, conv_id: int) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID.

        Args:
            conv_id: Conversation ID

        Returns:
            Conversation dictionary or None
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get conversation
            cursor.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conv_id,))

            row = cursor.fetchone()
            if not row:
                return None

            conv = dict(row)

            # Get sources
            cursor.execute("""
                SELECT * FROM conversation_sources
                WHERE conversation_id = ?
                ORDER BY similarity_score DESC
            """, (conv_id,))

            conv['sources'] = [dict(r) for r in cursor.fetchall()]

            return conv

    def get_recent_conversations(
        self,
        limit: int = 10,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get recent conversations.

        Args:
            limit: Maximum number of conversations
            session_id: Optional session filter

        Returns:
            List of conversation dictionaries
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if session_id:
                cursor.execute("""
                    SELECT * FROM conversations
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def search_conversations(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations by question or answer.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching conversations
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM conversations
                WHERE question LIKE ? OR answer LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))

            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics.

        Returns:
            Statistics dictionary
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Total conversations
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total = cursor.fetchone()[0]

            # Conversations by provider
            cursor.execute("""
                SELECT llm_provider, COUNT(*) as count
                FROM conversations
                GROUP BY llm_provider
            """)
            by_provider = {row[0]: row[1] for row in cursor.fetchall()}

            # Average sources per conversation
            cursor.execute("""
                SELECT AVG(source_count) FROM conversations
            """)
            avg_sources = cursor.fetchone()[0] or 0

            # Most queried books
            cursor.execute("""
                SELECT book_title, COUNT(*) as count
                FROM conversation_sources
                GROUP BY book_title
                ORDER BY count DESC
                LIMIT 10
            """)
            top_books = [{'title': row[0], 'count': row[1]} for row in cursor.fetchall()]

            return {
                'total_conversations': total,
                'by_provider': by_provider,
                'avg_sources_per_conversation': avg_sources,
                'most_referenced_books': top_books,
            }

    def clear_old_conversations(self, days: int = 30) -> int:
        """Delete conversations older than N days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted conversations
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM conversations
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))

            deleted = cursor.rowcount
            conn.commit()

        self._log('info', f"Deleted {deleted} old conversations")
        return deleted

    def export_to_json(self, filepath: str, limit: int = None) -> None:
        """Export conversation history to JSON.

        Args:
            filepath: Output file path
            limit: Optional limit on number of conversations
        """
        conversations = self.get_recent_conversations(limit or 1000)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)

        self._log('info', f"Exported conversation history to {filepath}")
