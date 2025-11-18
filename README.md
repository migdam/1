# 📚 AI Library & Knowledge Engine

A comprehensive local-first RAG (Retrieval-Augmented Generation) system for semantic search and AI-powered querying across your entire book collection.

## ✨ Features

- **Multi-Format Support**: Process PDF, EPUB, MOBI, DOCX, TXT, HTML, and more
- **Local Embeddings**: Free, offline embedding generation using SentenceTransformers
- **Vector Database**: Fast semantic search using FAISS
- **Multiple LLM Providers**: Support for OpenAI, Google Gemini, Anthropic Claude, and local Ollama models
- **Smart Chunking**: Intelligent text segmentation respecting paragraphs and sentences
- **Metadata Tracking**: SQLite database for comprehensive book and chunk metadata
- **Interactive CLI**: Beautiful command-line interface for querying your library
- **Scalable**: Handle thousands of books and millions of embeddings
- **Privacy-First**: Fully local processing (optional cloud LLM)

## 🏗️ Architecture

```
Books → Text Extraction → Chunking → Embeddings → Vector DB
                                                       ↓
User Query → Embedding → Similarity Search → Context → LLM → Answer
```

## 📋 Requirements

- Python 3.8+
- 4GB+ RAM (8GB+ recommended)
- Storage space for books and vector database

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-library-rag-system

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.yaml` to customize your setup:

```yaml
# Choose your LLM provider
llm:
  provider: "local"  # Options: openai, gemini, claude, local

# Configure embedding model
embedding:
  model: "intfloat/e5-small-v2"  # Fast and accurate
  device: "cpu"

# Set paths
paths:
  books: "./books"
  vector_db: "./data/books_index"
  metadata_db: "./data/books_metadata.db"
```

### 3. Add Books

Place your book files in the `./books` directory:

```bash
mkdir -p books
# Copy your books here
cp ~/Documents/MyBooks/*.pdf books/
```

### 4. Build Vector Database

Process your books and build the searchable index:

```bash
python build_vector_base.py
```

This will:
- Extract text from all books
- Create semantic chunks
- Generate embeddings
- Build vector database
- Create metadata index

### 5. Query Your Library

**Interactive mode:**

```bash
python rag_query.py
```

**Single query:**

```bash
python rag_query.py --query "What is the meaning of life according to philosophy books?"
```

## 🔧 Configuration Options

### Embedding Models

Choose from these high-quality local models:

- `intfloat/e5-small-v2` (Recommended) - 384 dimensions, fast and accurate
- `all-MiniLM-L6-v2` - 384 dimensions, very fast
- `paraphrase-multilingual-MiniLM-L12-v2` - Multilingual support

### LLM Providers

#### OpenAI

```yaml
llm:
  provider: "openai"
  openai:
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"
```

Set environment variable:
```bash
export OPENAI_API_KEY="your-api-key"
```

#### Google Gemini

```yaml
llm:
  provider: "gemini"
  gemini:
    model: "gemini-2.0-flash-exp"
    api_key_env: "GEMINI_API_KEY"
```

Set environment variable:
```bash
export GEMINI_API_KEY="your-api-key"
```

#### Anthropic Claude

```yaml
llm:
  provider: "claude"
  claude:
    model: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"
```

Set environment variable:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

#### Local (Ollama)

```yaml
llm:
  provider: "local"
  ollama:
    model: "gemma2:9b"
    host: "http://localhost:11434"
```

First, install Ollama from https://ollama.ai, then:

```bash
ollama pull gemma2:9b
# or
ollama pull llama3.1:8b
ollama pull mistral
```

### Chunking Settings

```yaml
chunking:
  chunk_size: 1000          # Target chunk size in words
  chunk_overlap: 100        # Overlap between chunks
  min_chunk_size: 200       # Minimum chunk size
  max_chunk_size: 1500      # Maximum chunk size
  respect_paragraphs: true  # Keep paragraphs intact
  respect_sentences: true   # Keep sentences intact
```

### RAG Settings

```yaml
rag:
  top_k: 5                      # Number of chunks to retrieve
  similarity_threshold: 0.3     # Minimum similarity score
  max_context_length: 4000      # Maximum context characters
  include_metadata: true        # Include book metadata
```

## 📖 Usage Examples

### Basic Query

```bash
python rag_query.py
```

```
❯ What are the main principles of stoic philosophy?

Answer:
Based on the excerpts, the main principles of Stoic philosophy include:

1. **Focus on what you can control** [1] - Stoics emphasize distinguishing
   between things within our control (our thoughts, actions, attitudes) and
   things outside our control (external events, other people's opinions).

2. **Live in accordance with nature** [2, 3] - This means accepting the
   natural order of things and living virtuously...

Sources:
[1] Meditations by Marcus Aurelius (Score: 0.8945)
[2] The Enchiridion by Epictetus (Score: 0.8721)
[3] Letters from a Stoic by Seneca (Score: 0.8534)
```

### Extract Text Only

```bash
# Extract text from all books
python extract_text.py

# Extract from specific directory
python extract_text.py --input ~/Documents/Books --output ./extracted

# Extract only PDFs
python extract_text.py --format pdf
```

### Advanced Queries

```bash
# Use specific LLM provider
python rag_query.py --provider openai --query "Compare Kant and Hume on causality"

# Retrieve more context
python rag_query.py --top-k 10 --query "What is consciousness?"

# Single query without sources
python rag_query.py --query "Summarize quantum mechanics" --no-sources
```

## 📊 Database Statistics

View your library statistics:

```python
from src.metadata_db import MetadataDB

db = MetadataDB("./data/books_metadata.db")
stats = db.get_stats()

print(f"Total books: {stats['total_books']}")
print(f"Total chunks: {stats['total_chunks']}")
print(f"Total words: {stats['total_words']:,}")
```

## 🔍 How It Works

### 1. Text Extraction

The system extracts text from various formats:

- **PDF**: PyMuPDF with text layer extraction
- **EPUB**: ebooklib with HTML parsing
- **DOCX**: python-docx for Word documents
- **TXT**: Encoding detection with chardet
- **HTML**: BeautifulSoup for web pages

### 2. Chunking

Text is split into semantic chunks:

- Respects paragraph and sentence boundaries
- Configurable size with overlap
- Maintains context between chunks
- Stores position metadata

### 3. Embedding Generation

Creates vector representations:

- Uses SentenceTransformers
- Batch processing for efficiency
- Normalized embeddings for cosine similarity
- Optional caching

### 4. Vector Database

FAISS-based similarity search:

- Efficient nearest neighbor search
- Supports millions of vectors
- Persistent disk storage
- Metadata association

### 5. Retrieval & Generation

RAG pipeline:

1. Encode user query to vector
2. Search for similar chunks
3. Retrieve relevant context
4. Build prompt with context
5. Generate answer with LLM
6. Cite sources

## 🎯 Performance Tips

### For Large Collections (1000+ books):

1. **Use GPU for embeddings** (if available):
   ```yaml
   embedding:
     device: "cuda"
   ```

2. **Increase batch sizes**:
   ```yaml
   embedding:
     batch_size: 64
   processing:
     batch_size: 20
   ```

3. **Use IVF index for faster search**:
   ```yaml
   vector_db:
     index_type: "IndexIVFFlat"
   ```

### For Better Quality:

1. **Increase chunk size**:
   ```yaml
   chunking:
     chunk_size: 1500
     chunk_overlap: 200
   ```

2. **Retrieve more context**:
   ```yaml
   rag:
     top_k: 10
     max_context_length: 8000
   ```

3. **Use better embedding model**:
   ```yaml
   embedding:
     model: "sentence-transformers/all-mpnet-base-v2"
   ```

## 🛠️ Development

### Project Structure

```
ai-library-rag-system/
├── src/
│   ├── config_loader.py      # Configuration management
│   ├── logger.py              # Logging system
│   ├── metadata_db.py         # SQLite metadata database
│   ├── text_extractor.py      # Multi-format text extraction
│   ├── chunker.py             # Text chunking logic
│   ├── embedder.py            # Embedding generation
│   ├── vector_db.py           # FAISS vector database
│   ├── llm_client.py          # LLM provider integration
│   └── retriever.py           # RAG retrieval pipeline
├── build_vector_base.py       # Build vector database
├── rag_query.py               # Query interface
├── extract_text.py            # Text extraction tool
├── config.yaml                # Configuration file
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### Adding New Features

1. **Custom LLM Provider**: Extend `BaseLLM` in `llm_client.py`
2. **New Book Format**: Add extractor in `text_extractor.py`
3. **Alternative Vector DB**: Implement interface in `vector_db.py`
4. **Custom Chunking**: Modify `chunker.py` strategies

## 🐛 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt
```

**Ollama connection error:**
```bash
# Start Ollama
ollama serve

# In another terminal
ollama pull gemma2:9b
```

**Out of memory during processing:**
```yaml
processing:
  batch_size: 5
embedding:
  batch_size: 16
```

**Poor search results:**
- Increase `top_k` in config
- Lower `similarity_threshold`
- Try different embedding model
- Check book text quality with `extract_text.py`

## 📝 Environment Variables

Create a `.env` file:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
HF_HOME=./models  # HuggingFace cache directory
```

## 🚧 Future Enhancements

- [ ] Agentic metadata extraction (auto-detect authors, dates, genres)
- [ ] Automatic book summarization
- [ ] Auto-tagging and categorization
- [ ] Cross-encoder reranking
- [ ] Multi-vector search (hybrid BM25 + embeddings)
- [ ] Web UI with NiceGUI
- [ ] PDF preview in results
- [ ] Chapter-aware chunking
- [ ] Named entity recognition
- [ ] Quote extraction engine
- [ ] MCP (Model Context Protocol) integration
- [ ] Multi-language support

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review configuration examples

## 🙏 Acknowledgments

Built with:
- [SentenceTransformers](https://www.sbert.net/) - Embedding models
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing
- [ebooklib](https://github.com/aerkalov/ebooklib) - EPUB processing
- [Ollama](https://ollama.ai/) - Local LLM runtime

---

**Built with ❤️ for book lovers and knowledge seekers**
