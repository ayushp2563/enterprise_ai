import logging
import time
from typing import List, Dict, Any, Tuple
from app.services.document_ingestion import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.services.llm_service import get_llm_service
from app.services.hr_escalation_service import get_hr_escalation_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation engine with multi-tenancy and HR escalation."""
    
    def __init__(self):
        """Initialize the RAG engine."""
        self.ingestion_service = get_ingestion_service()
        self.vector_store = get_vector_store()
        self.llm_service = get_llm_service()
        self.hr_escalation_service = get_hr_escalation_service()
        logger.info("Initialized RAG Engine with HR escalation support")
    
    def query(
        self,
        question: str,
        company_id: int,
        user_id: int,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG with company-scoped data and HR escalation.
        
        Args:
            question: User question
            company_id: Company ID for data isolation
            user_id: User ID for logging and escalation
            top_k: Number of context chunks to retrieve
            
        Returns:
            Dictionary with answer, sources, metadata, and HR escalation info
        """
        start_time = time.time()
        
        if top_k is None:
            top_k = settings.top_k_results
        
        try:
            # Generate query embedding
            logger.info(f"Processing query for company {company_id}: {question}")
            query_embedding = self.ingestion_service.generate_embeddings([question])[0]
            
            # Retrieve relevant context (company-scoped)
            similar_chunks = self.vector_store.similarity_search(
                query_embedding=query_embedding,
                company_id=company_id,
                top_k=top_k
            )
            
            # Extract similarity scores
            similarity_scores = [chunk['similarity'] for chunk in similar_chunks]
            
            # Check if we should escalate to HR
            should_escalate, escalation_reason = self.hr_escalation_service.should_escalate_to_hr(
                question=question,
                confidence_score=0.0,  # Will be calculated below
                num_sources=len(similar_chunks)
            )
            
            # Handle no results case
            if not similar_chunks:
                confidence_score = 0.0
                answer = "I don't have enough information in our policy documents to answer this question."
                sources = []
                
                # Always escalate when no documents found
                should_escalate = True
                escalation_reason = "No relevant policy documents found"
            else:
                # Build context from retrieved chunks
                context = self._build_context(similar_chunks)
                
                # Generate answer using LLM
                answer = self._generate_answer(question, context)
                
                # Prepare sources
                sources = self._prepare_sources(similar_chunks)
                
                # Calculate confidence score
                confidence_score = self.hr_escalation_service.calculate_confidence_score(
                    similarity_scores=similarity_scores,
                    num_sources=len(similar_chunks),
                    answer_length=len(answer)
                )
                
                # Re-check escalation with calculated confidence
                should_escalate, escalation_reason = self.hr_escalation_service.should_escalate_to_hr(
                    question=question,
                    confidence_score=confidence_score,
                    num_sources=len(similar_chunks)
                )
            
            query_time = time.time() - start_time
            logger.info(f"Query completed in {query_time:.2f}s (confidence: {confidence_score:.2f}, escalate: {should_escalate})")
            
            # Prepare HR contact info if escalation needed
            hr_contact = None
            if should_escalate:
                hr_contact = {
                    "message": "This question may require HR assistance. Would you like to contact the HR department?",
                    "action": "create_escalation",
                    "reason": escalation_reason
                }
            
            return {
                "answer": answer,
                "sources": sources,
                "query_time": query_time,
                "model_used": settings.groq_model,
                "confidence_score": confidence_score,
                "should_escalate": should_escalate,
                "escalation_reason": escalation_reason,
                "hr_contact": hr_contact
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
            category = chunk.get('category', 'General')
            context_parts.append(
                f"[Source {idx}: {chunk['document_title']} - {category}]\\n{chunk['chunk_text']}\\n"
            )
        
        return "\\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using LLM with context.
        
        Args:
            question: User question
            context: Retrieved context
            
        Returns:
            Generated answer
        """
        system_message = """You are a helpful AI assistant for an enterprise company's HR policy system.
Your role is to answer employee questions based on company policy documents.

Guidelines:
- Answer questions accurately based ONLY on the context provided
- If the context doesn't contain enough information, say so clearly
- Cite specific policies when possible
- Be concise but comprehensive
- Maintain a professional and helpful tone
- If the question involves sensitive HR matters (harassment, discrimination, legal issues), suggest contacting HR directly"""

        prompt = f"""Context from company policy documents:
{context}

Employee Question: {question}

Please provide a clear and accurate answer based on the policy documents above. If the policies don't contain enough information to fully answer the question, state that clearly and suggest contacting HR if appropriate."""

        return self.llm_service.generate_response(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3,  # Lower temperature for more factual responses
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
                    "category": chunk.get('category', 'General'),
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
