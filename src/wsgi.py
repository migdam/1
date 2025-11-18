"""WSGI entry point for production deployment."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_config
from src.logger import init_global_logger
from src.metadata_db import MetadataDB
from src.embedder import create_embedder
from src.vector_db import load_vector_db
from src.llm_client import create_llm_from_config
from src.retriever import create_rag_pipeline
from src.production_api import ProductionAPI


def create_app():
    """Create and configure the Flask application.

    Returns:
        Flask app instance
    """
    # Load configuration
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    config = get_config(config_path)

    # Initialize logger
    logger = init_global_logger(config)
    logger.info("Initializing AI Library API...")

    try:
        # Load metadata database
        metadata_db = MetadataDB(str(config.metadata_db_path))
        logger.info(f"Loaded metadata database: {config.metadata_db_path}")

        # Load embedder
        embedder = create_embedder(
            model_name=config.embedding_model,
            device=config.embedding_device,
            batch_size=config.embedding_batch_size,
            cache_dir=config.get('embedding.cache_dir'),
            logger=logger
        )
        logger.info(f"Loaded embedder: {config.embedding_model}")

        # Load vector database
        vector_db = load_vector_db(str(config.vector_db_path), logger=logger)
        logger.info(f"Loaded vector database: {vector_db.size()} vectors")

        # Create LLM client
        llm_client = create_llm_from_config(config, logger=logger)
        logger.info(f"Initialized LLM client: {config.llm_provider}")

        # Create RAG pipeline
        rag_pipeline = create_rag_pipeline(
            embedder=embedder,
            vector_db=vector_db,
            metadata_db=metadata_db,
            llm_client=llm_client,
            config=config,
            logger=logger
        )
        logger.info("RAG pipeline initialized")

        # Create production API
        api = ProductionAPI(
            embedder=embedder,
            vector_db=vector_db,
            metadata_db=metadata_db,
            llm_client=llm_client,
            rag_pipeline=rag_pipeline,
            config=config,
            logger=logger
        )

        app = api.create_app()
        logger.info("AI Library API ready")

        return app

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise


# Create the application instance
app = create_app()

if __name__ == '__main__':
    # For development only
    port = int(os.getenv('API_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
