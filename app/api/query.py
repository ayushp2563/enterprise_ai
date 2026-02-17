import logging
import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.documents import QueryRequest, QueryResponse
from app.services.rag_engine import get_rag_engine, RAGEngine
from app.services.hr_escalation_service import get_hr_escalation_service, HREscalationService
from app.security.auth import get_current_user
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/query", tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    rag_engine: RAGEngine = Depends(get_rag_engine)
) -> QueryResponse:
    """
    Query company policy documents using RAG with HR escalation.
    
    Requires: Authentication (any role)
    """
    try:
        logger.info(f"User {current_user['email']} querying: {request.question[:100]}...")
        
        # Process query with company-scoped RAG
        result = rag_engine.query(
            question=request.question,
            company_id=current_user["company_id"],
            user_id=current_user["id"],
            top_k=request.top_k
        )
        
        # Log query to database
        try:
            connection = psycopg2.connect(settings.database_url)
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO query_logs 
                    (company_id, user_id, question, answer, sources, query_time, 
                     confidence_score, escalated_to_hr)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    current_user["company_id"],
                    current_user["id"],
                    request.question,
                    result["answer"],
                    {"sources": result["sources"]},
                    result["query_time"],
                    result["confidence_score"],
                    result["should_escalate"]
                ))
                query_log_id = cursor.fetchone()[0]
                connection.commit()
                
                # If escalation recommended, create escalation record
                if result["should_escalate"]:
                    hr_service = get_hr_escalation_service()
                    hr_service.create_escalation(
                        company_id=current_user["company_id"],
                        user_id=current_user["id"],
                        question=request.question,
                        reason=result["escalation_reason"],
                        query_log_id=query_log_id
                    )
                    logger.info(f"Created HR escalation for query {query_log_id}")
                
            connection.close()
        except Exception as log_error:
            logger.error(f"Error logging query: {str(log_error)}")
            # Don't fail the request if logging fails
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing query"
        )


@router.get("/history")
async def get_query_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Get query history for the current user.
    
    Requires: Authentication (any role)
    """
    try:
        connection = psycopg2.connect(settings.database_url)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, question, answer, confidence_score, escalated_to_hr, created_at
                FROM query_logs
                WHERE company_id = %s AND user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (current_user["company_id"], current_user["id"], limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "id": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "confidence_score": row[3],
                    "escalated_to_hr": row[4],
                    "created_at": row[5]
                })
        
        connection.close()
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error getting query history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving query history"
        )
