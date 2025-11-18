"""Retrieval pipeline for semantic search and RAG."""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    """Represents a retrieval result."""

    chunk_text: str
    book_title: str
    book_author: str
    similarity_score: float
    chunk_index: int
    book_id: int
    metadata: Dict[str, Any]

    def __str__(self) -> str:
        """String representation."""
        return (
            f"[Score: {self.similarity_score:.4f}] "
            f"{self.book_title} by {self.book_author}\n"
            f"{self.chunk_text[:200]}..."
        )


class Retriever:
    """Retrieval pipeline for semantic search."""

    def __init__(
        self,
        embedder,
        vector_db,
        metadata_db,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        logger=None
    ):
        """Initialize retriever.

        Args:
            embedder: Embedder instance for encoding queries
            vector_db: VectorDB instance for similarity search
            metadata_db: MetadataDB instance for chunk/book metadata
            top_k: Number of results to retrieve
            similarity_threshold: Minimum similarity score
            logger: Optional logger instance
        """
        self.embedder = embedder
        self.vector_db = vector_db
        self.metadata_db = metadata_db
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant chunks for a query.

        Args:
            query: Search query
            top_k: Optional override for number of results
            filters: Optional metadata filters

        Returns:
            List of RetrievalResult objects
        """
        if top_k is None:
            top_k = self.top_k

        self._log('debug', f"Retrieving top-{top_k} results for query: {query[:100]}")

        # Encode query
        query_embedding = self.embedder.encode(query, show_progress=False)

        # Search vector database
        raw_results = self.vector_db.search(
            query_embedding,
            k=top_k * 2,  # Get more to allow for filtering
            return_metadata=True
        )

        # Process results
        results = []
        for vector_id, similarity, chunk_metadata in raw_results:
            # Skip if below threshold
            if similarity < self.similarity_threshold:
                continue

            # Get chunk details from metadata DB
            chunk_data = self.metadata_db.get_chunk_by_vector_id(vector_id)
            if not chunk_data:
                self._log('warning', f"No chunk data found for vector_id {vector_id}")
                continue

            # Get book details
            book_data = self.metadata_db.get_book(chunk_data['book_id'])
            if not book_data:
                self._log('warning', f"No book data found for book_id {chunk_data['book_id']}")
                continue

            # Apply filters if specified
            if filters:
                if not self._apply_filters(book_data, chunk_data, filters):
                    continue

            # Create result
            result = RetrievalResult(
                chunk_text=chunk_data['chunk_text'],
                book_title=book_data.get('title', 'Unknown'),
                book_author=book_data.get('author', 'Unknown'),
                similarity_score=similarity,
                chunk_index=chunk_data['chunk_index'],
                book_id=chunk_data['book_id'],
                metadata={
                    'book': book_data,
                    'chunk': chunk_data,
                    'vector_metadata': chunk_metadata
                }
            )

            results.append(result)

            # Stop if we have enough results
            if len(results) >= top_k:
                break

        self._log('info', f"Retrieved {len(results)} results")
        return results

    def _apply_filters(
        self,
        book_data: Dict[str, Any],
        chunk_data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Apply metadata filters to a result.

        Args:
            book_data: Book metadata
            chunk_data: Chunk metadata
            filters: Filter criteria

        Returns:
            True if result matches filters
        """
        for key, value in filters.items():
            # Check in book data
            if key in book_data:
                if book_data[key] != value:
                    return False

            # Check in chunk data
            elif key in chunk_data:
                if chunk_data[key] != value:
                    return False

        return True

    def build_context(
        self,
        results: List[RetrievalResult],
        max_length: Optional[int] = None,
        include_metadata: bool = True
    ) -> str:
        """Build context string from retrieval results.

        Args:
            results: List of retrieval results
            max_length: Optional maximum context length in characters
            include_metadata: Whether to include metadata in context

        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            # Format result
            if include_metadata:
                part = (
                    f"[{i}] {result.book_title} by {result.book_author}\n"
                    f"{result.chunk_text}\n"
                )
            else:
                part = f"[{i}] {result.chunk_text}\n"

            # Check length limit
            if max_length and (current_length + len(part)) > max_length:
                break

            context_parts.append(part)
            current_length += len(part)

        return "\n".join(context_parts)


class RAGPipeline:
    """Complete RAG pipeline combining retrieval and generation."""

    def __init__(
        self,
        retriever: Retriever,
        llm_client,
        logger=None
    ):
        """Initialize RAG pipeline.

        Args:
            retriever: Retriever instance
            llm_client: LLM client instance
            logger: Optional logger instance
        """
        self.retriever = retriever
        self.llm_client = llm_client
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available."""
        if self.logger:
            getattr(self.logger, level)(message)

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        max_context_length: Optional[int] = None,
        temperature: float = 0.7,
        custom_prompt: Optional[str] = None
    ) -> Tuple[str, List[RetrievalResult]]:
        """Query the knowledge base with RAG.

        Args:
            question: User question
            top_k: Optional number of chunks to retrieve
            max_context_length: Optional maximum context length
            temperature: LLM temperature
            custom_prompt: Optional custom prompt template

        Returns:
            Tuple of (answer, retrieval_results)
        """
        self._log('info', f"RAG query: {question[:100]}")

        # Retrieve relevant chunks
        results = self.retriever.retrieve(question, top_k=top_k)

        if not results:
            self._log('warning', "No relevant results found")
            return "I couldn't find any relevant information to answer your question.", []

        # Build context
        context = self.retriever.build_context(
            results,
            max_length=max_context_length,
            include_metadata=True
        )

        # Build prompt
        if custom_prompt:
            prompt = custom_prompt.format(context=context, query=question)
        else:
            prompt = self._build_default_prompt(context, question)

        self._log('debug', f"Generated prompt of length {len(prompt)}")

        # Generate answer
        try:
            answer = self.llm_client.generate(prompt, temperature=temperature)
            self._log('info', "Generated answer successfully")
        except Exception as e:
            self._log('error', f"Error generating answer: {str(e)}")
            answer = f"Error generating answer: {str(e)}"

        return answer, results

    def _build_default_prompt(self, context: str, query: str) -> str:
        """Build default RAG prompt.

        Args:
            context: Context from retrieval
            query: User query

        Returns:
            Formatted prompt
        """
        prompt = f"""You are an expert AI librarian with access to a vast collection of books.

Use ONLY the following book excerpts to answer the question.
If the information is not in the excerpts, say so clearly.
Cite sources by referring to the excerpt numbers (e.g., [1], [2]).

Book Excerpts:
{context}

Question:
{query}

Please provide a detailed answer based on the excerpts above, citing sources:"""

        return prompt

    def batch_query(
        self,
        questions: List[str],
        top_k: Optional[int] = None,
        max_context_length: Optional[int] = None,
        temperature: float = 0.7
    ) -> List[Tuple[str, List[RetrievalResult]]]:
        """Process multiple queries.

        Args:
            questions: List of questions
            top_k: Optional number of chunks to retrieve
            max_context_length: Optional maximum context length
            temperature: LLM temperature

        Returns:
            List of (answer, results) tuples
        """
        answers = []

        for question in questions:
            answer, results = self.query(
                question,
                top_k=top_k,
                max_context_length=max_context_length,
                temperature=temperature
            )
            answers.append((answer, results))

        return answers


def create_rag_pipeline(
    embedder,
    vector_db,
    metadata_db,
    llm_client,
    config=None,
    logger=None
) -> RAGPipeline:
    """Create a complete RAG pipeline.

    Args:
        embedder: Embedder instance
        vector_db: VectorDB instance
        metadata_db: MetadataDB instance
        llm_client: LLM client instance
        config: Optional configuration object
        logger: Optional logger instance

    Returns:
        RAGPipeline instance
    """
    # Create retriever
    if config:
        top_k = config.get('rag.top_k', 5)
        threshold = config.get('rag.similarity_threshold', 0.0)
    else:
        top_k = 5
        threshold = 0.0

    retriever = Retriever(
        embedder=embedder,
        vector_db=vector_db,
        metadata_db=metadata_db,
        top_k=top_k,
        similarity_threshold=threshold,
        logger=logger
    )

    # Create RAG pipeline
    pipeline = RAGPipeline(
        retriever=retriever,
        llm_client=llm_client,
        logger=logger
    )

    return pipeline
