import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.documents import QueryRequest, QueryResponse
from app.services.rag_engine import get_rag_engine
from app.security.auth import verify_api_key, sanitize_input

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    api_key: str = Depends(verify_api_key)
) -> QueryResponse:
    """
    Query documents using RAG.
    
    Args:
        request: Query request with question
        api_key: Validated API key
        
    Returns:
        Query response with answer and sources
    """
    try:
        # Sanitize input
        question = sanitize_input(request.question, max_length=1000)
        
        logger.info(f"Received query: {question[:100]}...")
        
        # Get RAG engine and process query
        rag_engine = get_rag_engine()
        result = rag_engine.query(
            question=question,
            top_k=request.top_k
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "query"}
