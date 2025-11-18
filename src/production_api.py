"""Production-ready API server with security, monitoring, and performance features."""

import os
import time
import hashlib
import jwt
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import threading

try:
    from flask import Flask, request, jsonify, g
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


class SecurityManager:
    """Handle authentication and authorization."""

    def __init__(self, secret_key: str, api_keys: list = None):
        """Initialize security manager.

        Args:
            secret_key: Secret key for JWT
            api_keys: List of valid API keys
        """
        self.secret_key = secret_key
        self.api_keys = set(api_keys or [])

    def generate_token(self, user_id: str, expiry: int = 3600) -> str:
        """Generate JWT token.

        Args:
            user_id: User identifier
            expiry: Token expiry in seconds

        Returns:
            JWT token string
        """
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expiry),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token.

        Args:
            token: JWT token

        Returns:
            Decoded payload or None
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key.

        Args:
            api_key: API key to verify

        Returns:
            True if valid
        """
        return api_key in self.api_keys


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, per_minute: int = 60, per_hour: int = 1000):
        """Initialize rate limiter.

        Args:
            per_minute: Max requests per minute
            per_hour: Max requests per hour
        """
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed.

        Args:
            key: Client identifier (IP, user_id, etc.)

        Returns:
            True if allowed
        """
        now = time.time()

        with self.lock:
            # Clean old entries
            self.requests[key] = [
                ts for ts in self.requests[key]
                if now - ts < 3600  # Keep last hour
            ]

            # Check limits
            recent_minute = [ts for ts in self.requests[key] if now - ts < 60]
            recent_hour = self.requests[key]

            if len(recent_minute) >= self.per_minute:
                return False

            if len(recent_hour) >= self.per_hour:
                return False

            # Add current request
            self.requests[key].append(now)
            return True


class MetricsCollector:
    """Collect application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_error': 0,
            'response_times': [],
            'active_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'llm_calls': 0,
            'vector_searches': 0,
        }
        self.lock = threading.Lock()

    def increment(self, metric: str, value: int = 1):
        """Increment a metric.

        Args:
            metric: Metric name
            value: Value to add
        """
        with self.lock:
            if metric in self.metrics:
                self.metrics[metric] += value

    def record_response_time(self, duration: float):
        """Record response time.

        Args:
            duration: Response time in seconds
        """
        with self.lock:
            self.metrics['response_times'].append(duration)
            # Keep only last 1000
            if len(self.metrics['response_times']) > 1000:
                self.metrics['response_times'] = self.metrics['response_times'][-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.

        Returns:
            Metrics dictionary
        """
        with self.lock:
            avg_response_time = (
                sum(self.metrics['response_times']) / len(self.metrics['response_times'])
                if self.metrics['response_times'] else 0
            )

            return {
                **self.metrics,
                'avg_response_time': avg_response_time,
                'response_time_count': len(self.metrics['response_times']),
            }


class ProductionAPI:
    """Production-ready API server."""

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
        """Initialize production API.

        Args:
            embedder: Embedder instance
            vector_db: VectorDB instance
            metadata_db: MetadataDB instance
            llm_client: LLM client
            rag_pipeline: RAG pipeline
            config: Configuration object
            logger: Optional logger
        """
        if not HAS_FLASK:
            raise ImportError("Flask is required. Install with: pip install flask flask-cors flask-limiter")

        self.embedder = embedder
        self.vector_db = vector_db
        self.metadata_db = metadata_db
        self.llm_client = llm_client
        self.rag_pipeline = rag_pipeline
        self.config = config
        self.logger = logger

        # Security
        secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
        api_keys = os.getenv('ALLOWED_API_KEYS', '').split(',')
        self.security = SecurityManager(secret_key, [k.strip() for k in api_keys if k.strip()])

        # Rate limiting
        self.rate_limiter = RateLimiter(
            per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', 60)),
            per_hour=int(os.getenv('RATE_LIMIT_PER_HOUR', 1000))
        )

        # Metrics
        self.metrics = MetricsCollector()

        self.app = None

    def create_app(self):
        """Create Flask application with production features.

        Returns:
            Flask app
        """
        app = Flask(__name__)

        # Configuration
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
        app.config['JSON_SORT_KEYS'] = False
        app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE', 104857600))

        # CORS
        cors_origins = os.getenv('CORS_ORIGINS', '*')
        if cors_origins != '*':
            cors_origins = cors_origins.split(',')
        CORS(app, origins=cors_origins)

        # Request tracking middleware
        @app.before_request
        def before_request():
            """Track request start time."""
            g.start_time = time.time()
            self.metrics.increment('active_requests')

        @app.after_request
        def after_request(response):
            """Track request completion."""
            duration = time.time() - g.start_time
            self.metrics.increment('active_requests', -1)
            self.metrics.record_response_time(duration)

            if response.status_code < 400:
                self.metrics.increment('requests_success')
            else:
                self.metrics.increment('requests_error')

            # Add response headers
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')

            return response

        # Authentication decorator
        def require_auth(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if not os.getenv('ENABLE_AUTH', 'false').lower() == 'true':
                    return f(*args, **kwargs)

                # Check API key
                api_key = request.headers.get(os.getenv('API_KEY_HEADER', 'X-API-Key'))
                if api_key and self.security.verify_api_key(api_key):
                    return f(*args, **kwargs)

                # Check JWT token
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    payload = self.security.verify_token(token)
                    if payload:
                        g.user_id = payload.get('user_id')
                        return f(*args, **kwargs)

                return jsonify({'error': 'Unauthorized'}), 401

            return decorated

        # Rate limiting decorator
        def rate_limit(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                if not os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true':
                    return f(*args, **kwargs)

                client_id = request.remote_addr
                if not self.rate_limiter.is_allowed(client_id):
                    return jsonify({'error': 'Rate limit exceeded'}), 429

                return f(*args, **kwargs)

            return decorated

        # Routes
        @app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            try:
                # Check vector DB
                vector_db_size = self.vector_db.size()

                # Check metadata DB
                stats = self.metadata_db.get_stats()

                health_status = {
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': os.getenv('APP_VERSION', '1.0.0'),
                    'components': {
                        'vector_db': {
                            'status': 'healthy',
                            'size': vector_db_size
                        },
                        'metadata_db': {
                            'status': 'healthy',
                            'total_books': stats['total_books']
                        },
                        'embedder': {
                            'status': 'healthy',
                            'model': self.embedder.model_name
                        }
                    }
                }

                return jsonify(health_status)

            except Exception as e:
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e)
                }), 503

        @app.route('/metrics', methods=['GET'])
        def metrics():
            """Prometheus-compatible metrics endpoint."""
            metrics_data = self.metrics.get_metrics()

            # Prometheus format
            output = []
            for key, value in metrics_data.items():
                if isinstance(value, (int, float)):
                    output.append(f"ai_library_{key} {value}")

            return '\n'.join(output), 200, {'Content-Type': 'text/plain'}

        @app.route('/stats', methods=['GET'])
        @require_auth
        def stats():
            """Get library statistics."""
            self.metrics.increment('requests_total')
            return jsonify(self.metadata_db.get_stats())

        @app.route('/books', methods=['GET'])
        @require_auth
        @rate_limit
        def list_books():
            """List all books."""
            self.metrics.increment('requests_total')

            status = request.args.get('status')
            limit = request.args.get('limit', type=int, default=100)

            books = self.metadata_db.list_books(status=status, limit=limit)
            return jsonify({'books': books, 'count': len(books)})

        @app.route('/books/<int:book_id>', methods=['GET'])
        @require_auth
        @rate_limit
        def get_book(book_id):
            """Get book details."""
            self.metrics.increment('requests_total')

            book = self.metadata_db.get_book(book_id)

            if not book:
                return jsonify({'error': 'Book not found'}), 404

            return jsonify({'book': book})

        @app.route('/search', methods=['POST'])
        @require_auth
        @rate_limit
        def search():
            """Semantic search."""
            self.metrics.increment('requests_total')
            self.metrics.increment('vector_searches')

            data = request.json

            if not data or 'query' not in data:
                return jsonify({'error': 'Query required'}), 400

            query = data['query']
            top_k = data.get('top_k', 5)

            try:
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
                    ],
                    'count': len(results)
                })

            except Exception as e:
                self.logger.error(f"Search error: {str(e)}")
                return jsonify({'error': 'Search failed'}), 500

        @app.route('/query', methods=['POST'])
        @require_auth
        @rate_limit
        def query():
            """RAG query."""
            self.metrics.increment('requests_total')
            self.metrics.increment('llm_calls')

            data = request.json

            if not data or 'question' not in data:
                return jsonify({'error': 'Question required'}), 400

            question = data['question']
            top_k = data.get('top_k')

            try:
                answer, results = self.rag_pipeline.query(question, top_k=top_k)

                return jsonify({
                    'question': question,
                    'answer': answer,
                    'sources': [
                        {
                            'book_title': r.book_title,
                            'book_author': r.book_author,
                            'similarity_score': r.similarity_score,
                        }
                        for r in results
                    ],
                    'source_count': len(results)
                })

            except Exception as e:
                self.logger.error(f"Query error: {str(e)}")
                return jsonify({'error': 'Query failed'}), 500

        @app.errorhandler(404)
        def not_found(e):
            return jsonify({'error': 'Not found'}), 404

        @app.errorhandler(500)
        def internal_error(e):
            return jsonify({'error': 'Internal server error'}), 500

        self.app = app
        return app

    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """Run the production API server.

        Args:
            host: Host address
            port: Port number
        """
        if not self.app:
            self.create_app()

        # Use production WSGI server
        try:
            from waitress import serve

            if self.logger:
                self.logger.info(f"Starting production server on {host}:{port}")

            serve(self.app, host=host, port=port, threads=int(os.getenv('API_WORKERS', 4)))

        except ImportError:
            if self.logger:
                self.logger.warning("Waitress not installed, using Flask dev server")
                self.logger.warning("Install waitress for production: pip install waitress")

            self.app.run(host=host, port=port, debug=False)
