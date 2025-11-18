"""Web API server for AI Library (Flask-based)."""

from typing import Dict, Any
import json


class LibraryAPI:
    """RESTful API for AI Library."""

    def __init__(
        self,
        embedder,
        vector_db,
        metadata_db,
        llm_client,
        rag_pipeline,
        config,
        logger=None
    ):
        """Initialize API.

        Args:
            embedder: Embedder instance
            vector_db: VectorDB instance
            metadata_db: MetadataDB instance
            llm_client: LLM client
            rag_pipeline: RAG pipeline
            config: Configuration object
            logger: Optional logger
        """
        self.embedder = embedder
        self.vector_db = vector_db
        self.metadata_db = metadata_db
        self.llm_client = llm_client
        self.rag_pipeline = rag_pipeline
        self.config = config
        self.logger = logger
        self.app = None

    def create_app(self):
        """Create Flask application.

        Returns:
            Flask app
        """
        try:
            from flask import Flask, request, jsonify
            from flask_cors import CORS
        except ImportError:
            raise ImportError("Flask is not installed. Install with: pip install flask flask-cors")

        app = Flask(__name__)
        CORS(app)

        @app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'vector_db_size': self.vector_db.size(),
                'total_books': self.metadata_db.get_stats()['total_books'],
            })

        @app.route('/stats', methods=['GET'])
        def stats():
            """Get library statistics."""
            return jsonify(self.metadata_db.get_stats())

        @app.route('/books', methods=['GET'])
        def list_books():
            """List all books."""
            status = request.args.get('status')
            limit = request.args.get('limit', type=int, default=100)

            books = self.metadata_db.list_books(status=status, limit=limit)
            return jsonify({'books': books})

        @app.route('/books/<int:book_id>', methods=['GET'])
        def get_book(book_id):
            """Get book details."""
            book = self.metadata_db.get_book(book_id)

            if not book:
                return jsonify({'error': 'Book not found'}), 404

            # Get chunks
            chunks = self.metadata_db.get_chunks(book_id)

            return jsonify({
                'book': book,
                'chunk_count': len(chunks),
            })

        @app.route('/search', methods=['POST'])
        def search():
            """Semantic search."""
            data = request.json

            if not data or 'query' not in data:
                return jsonify({'error': 'Query required'}), 400

            query = data['query']
            top_k = data.get('top_k', 5)

            # Perform retrieval
            results = self.rag_pipeline.retriever.retrieve(query, top_k=top_k)

            return jsonify({
                'results': [
                    {
                        'book_title': r.book_title,
                        'book_author': r.book_author,
                        'chunk_text': r.chunk_text,
                        'similarity_score': r.similarity_score,
                        'chunk_index': r.chunk_index,
                    }
                    for r in results
                ]
            })

        @app.route('/query', methods=['POST'])
        def query():
            """RAG query."""
            data = request.json

            if not data or 'question' not in data:
                return jsonify({'error': 'Question required'}), 400

            question = data['question']
            top_k = data.get('top_k')

            # Perform RAG
            answer, results = self.rag_pipeline.query(
                question,
                top_k=top_k
            )

            return jsonify({
                'question': question,
                'answer': answer,
                'sources': [
                    {
                        'book_title': r.book_title,
                        'book_author': r.book_author,
                        'chunk_text': r.chunk_text[:200],
                        'similarity_score': r.similarity_score,
                    }
                    for r in results
                ]
            })

        @app.route('/embed', methods=['POST'])
        def embed():
            """Generate embeddings for text."""
            data = request.json

            if not data or 'text' not in data:
                return jsonify({'error': 'Text required'}), 400

            text = data['text']
            embedding = self.embedder.encode(text, show_progress=False)

            return jsonify({
                'embedding': embedding.tolist(),
                'dimension': len(embedding),
            })

        self.app = app
        return app

    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Run the API server.

        Args:
            host: Host address
            port: Port number
            debug: Debug mode
        """
        if not self.app:
            self.create_app()

        if self.logger:
            self.logger.info(f"Starting API server on {host}:{port}")

        self.app.run(host=host, port=port, debug=debug)
