import logging
import time
from typing import List, Dict, Any
from app.services.document_ingestion import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.services.llm_service import get_llm_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation engine."""
    
    def __init__(self):
        """Initialize the RAG engine."""
        self.ingestion_service = get_ingestion_service()
        self.vector_store = get_vector_store()
        self.llm_service = get_llm_service()
        logger.info("Initialized RAG Engine")
    
    def query(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            question: User question
            top_k: Number of context chunks to retrieve
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        start_time = time.time()
        
        if top_k is None:
            top_k = settings.top_k_results
        
        try:
            # Generate query embedding
            logger.info(f"Processing query: {question}")
            query_embedding = self.ingestion_service.generate_embeddings([question])[0]
            
            # Retrieve relevant context
            similar_chunks = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            if not similar_chunks:
                return {
                    "answer": "I don't have enough information to answer this question. Please provide more context or rephrase your question.",
                    "sources": [],
                    "query_time": time.time() - start_time,
                    "model_used": settings.groq_model
                }
            
            # Build context from retrieved chunks
            context = self._build_context(similar_chunks)
            
            # Generate answer using LLM
            answer = self._generate_answer(question, context)
            
            # Prepare sources
            sources = self._prepare_sources(similar_chunks)
            
            query_time = time.time() - start_time
            logger.info(f"Query completed in {query_time:.2f} seconds")
            
            return {
                "answer": answer,
                "sources": sources,
                "query_time": query_time,
                "model_used": settings.groq_model
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise
    
    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved chunks.
        
        Args:
            chunks: List of retrieved chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {idx}: {chunk['document_title']}]\n{chunk['chunk_text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM with context.
        
        Args:
            question: User question
            context: Retrieved context
            
        Returns:
            Generated answer
        """
        system_message = """You are a helpful AI assistant for an enterprise company. 
Your role is to answer questions based on the provided context from internal documents.

Guidelines:
- Answer questions accurately based on the context provided
- If the context doesn't contain enough information, say so clearly
- Cite sources when possible
- Be concise but comprehensive
- Maintain a professional tone"""

        prompt = f"""Context from internal documents:
{context}

Question: {question}

Please provide a clear and accurate answer based on the context above. If the context doesn't contain enough information to answer the question, please state that clearly."""

        return self.llm_service.generate_response(
            prompt=prompt,
            system_message=system_message,
            temperature=0.7,
            max_tokens=1024
        )
    
    def _prepare_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare source citations.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            List of source information
        """
        sources = []
        seen_docs = set()
        
        for chunk in chunks:
            doc_id = chunk['document_id']
            
            if doc_id not in seen_docs:
                sources.append({
                    "document_id": doc_id,
                    "title": chunk['document_title'],
                    "similarity": chunk['similarity'],
                    "metadata": chunk.get('metadata', {})
                })
                seen_docs.add(doc_id)
        
        return sources


# Singleton instance
_rag_engine = None


def get_rag_engine() -> RAGEngine:
    """Get singleton instance of RAG Engine."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
