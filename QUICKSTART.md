# 🚀 Quick Start Guide

Get your AI Library running in 5 minutes!

## Step 1: Installation (2 minutes)

```bash
# Clone the repository
git clone <repository-url>
cd ai-library-rag-system

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Setup (1 minute)

### Option A: Use Local LLM (Fully Offline)

1. Install Ollama from https://ollama.ai

2. Pull a model:
```bash
ollama pull gemma2:9b
```

3. Your `config.yaml` is already set to use local mode!

### Option B: Use Cloud LLM

1. Get an API key from:
   - OpenAI: https://platform.openai.com/api-keys
   - Google Gemini: https://makersuite.google.com/app/apikey
   - Anthropic: https://console.anthropic.com/

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API key
```

3. Update `config.yaml`:
```yaml
llm:
  provider: "openai"  # or "gemini" or "claude"
```

## Step 3: Add Books (30 seconds)

```bash
# Copy your books to the books directory
cp ~/Documents/MyBooks/*.pdf books/
cp ~/Documents/MyBooks/*.epub books/
```

Supported formats: PDF, EPUB, MOBI, DOCX, TXT, HTML

## Step 4: Build Index (1 minute per book)

```bash
python build_vector_base.py
```

This will:
- Extract text from all books
- Create searchable chunks
- Generate embeddings
- Build vector database

**First run will download the embedding model (~100MB)**

## Step 5: Query! (30 seconds)

```bash
python rag_query.py
```

Try some queries:
- "What is the meaning of life?"
- "Summarize the main themes in these books"
- "What do the authors say about happiness?"

## 🎉 Done!

You now have a fully functional AI-powered library!

## Next Steps

### Add More Books

Just drop books in the `books/` folder and run:
```bash
python build_vector_base.py
```

It will only process new books (skips existing ones).

### Customize Settings

Edit `config.yaml` to:
- Change chunk size (larger = more context)
- Adjust number of results (top_k)
- Switch LLM providers
- Configure paths

### Try Different Models

**Embedding models** (in `config.yaml`):
```yaml
embedding:
  model: "intfloat/e5-small-v2"  # Current (recommended)
  # model: "all-MiniLM-L6-v2"  # Faster
  # model: "all-mpnet-base-v2"  # More accurate
```

**Local LLMs** (requires Ollama):
```bash
# Install different models
ollama pull llama3.1:8b    # Meta's Llama
ollama pull mistral        # Mistral AI
ollama pull qwen2:7b       # Alibaba's Qwen
```

Update config:
```yaml
llm:
  ollama:
    model: "llama3.1:8b"
```

## Troubleshooting

### "No module named X"
```bash
pip install -r requirements.txt
```

### "Ollama connection refused"
```bash
ollama serve  # In one terminal
# Then run your query in another terminal
```

### "Out of memory"
Reduce batch sizes in `config.yaml`:
```yaml
embedding:
  batch_size: 16
processing:
  batch_size: 5
```

### "Poor search results"
Increase context in `config.yaml`:
```yaml
rag:
  top_k: 10  # Get more results
```

## Example Session

```bash
$ python rag_query.py

Loading AI Library...
LLM Provider: local
Embedding Model: intfloat/e5-small-v2
Loaded 1250 document chunks from 15 books
AI Library loaded successfully!

╭─────────────────────────────────────────────╮
│          Welcome to AI Library RAG          │
│                                             │
│ Ask questions about your book collection.  │
╰─────────────────────────────────────────────╯

❯ What is stoicism?

Searching knowledge base...

Answer:
Stoicism is an ancient Greek philosophy that teaches the
development of self-control and fortitude as a means of
overcoming destructive emotions. According to the texts
[1, 2], the central principles include:

1. Focus on what you can control
2. Accept what you cannot change
3. Live in accordance with nature and reason
4. Practice virtue in all circumstances

Sources:
[1] Meditations by Marcus Aurelius (Score: 0.8945)
    Preview: "You have power over your mind - not outside
    events. Realize this, and you will find strength..."

[2] The Enchiridion by Epictetus (Score: 0.8721)
    Preview: "Some things are in our control and others not.
    Things in our control are opinion, pursuit, desire..."

❯ quit

Goodbye!
```

## Performance Benchmarks

Typical performance on M2 Mac mini:

- **Text extraction**: ~5 seconds per book
- **Embedding generation**: ~10 seconds per book (100 chunks)
- **Vector database build**: ~15 seconds per book (total)
- **Query response**: ~2 seconds (local LLM)
- **Query response**: ~1 second (cloud LLM)

For 100 books: ~25 minutes total processing time

## Tips for Best Results

1. **Organize your books** by topic in subdirectories
2. **Use descriptive queries** - be specific about what you want
3. **Try different phrasings** if results aren't good
4. **Check sources** to verify information
5. **Experiment with settings** - there's no one-size-fits-all

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review [config.yaml](config.yaml) for all available options
- Look at the [troubleshooting section](#troubleshooting)
- Open an issue on GitHub

---

**Happy reading! 📚**
