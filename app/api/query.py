import logging
import psycopg2
from psycopg2.extras import Json
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
        connection = psycopg2.connect(settings.database_url)
        with connection:
            with connection.cursor() as cursor:
                if request.conversation_id:
                    cursor.execute("""
                        SELECT id
                        FROM conversations
                        WHERE id = %s
                          AND company_id = %s
                          AND user_id = %s
                          AND archived_at IS NULL
                    """, (
                        str(request.conversation_id),
                        current_user["company_id"],
                        current_user["id"],
                    ))
                    row = cursor.fetchone()
                    if not row:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conversation not found",
                        )
                    conversation_id = row[0]
                else:
                    cursor.execute("""
                        INSERT INTO conversations (company_id, user_id, title)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (
                        current_user["company_id"],
                        current_user["id"],
                        request.question[:120],
                    ))
                    conversation_id = cursor.fetchone()[0]
        connection.close()

        logger.info(
            "RAG query accepted",
            extra={
                "company_id": current_user["company_id"],
                "user_id": current_user["id"],
                "conversation_id": str(conversation_id),
            },
        )

        # Process query with company-scoped RAG
        result = rag_engine.query(
            question=request.question,
            company_id=current_user["company_id"],
            user_id=current_user["id"],
            top_k=request.top_k
        )
        
        # Persist the query log and conversation messages.
        try:
            connection = psycopg2.connect(settings.database_url)
            with connection:
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
                        Json({"sources": result["sources"]}),
                        result["query_time"],
                        result["confidence_score"],
                        result["should_escalate"],
                    ))
                    query_log_id = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT INTO messages (
                            company_id, conversation_id, user_id, role, content
                        )
                        VALUES (%s, %s, %s, 'user', %s)
                    """, (
                        current_user["company_id"],
                        str(conversation_id),
                        current_user["id"],
                        request.question,
                    ))
                    cursor.execute("""
                        INSERT INTO messages (
                            company_id, conversation_id, role, content,
                            citations, retrieval_metadata, model
                        )
                        VALUES (%s, %s, 'assistant', %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        current_user["company_id"],
                        str(conversation_id),
                        result["answer"],
                        Json(result["sources"]),
                        Json({
                            "confidence_score": result["confidence_score"],
                            "query_time": result["query_time"],
                            "retrieved_chunks": len(result["sources"]),
                        }),
                        result["model_used"],
                    ))
                    message_id = cursor.fetchone()[0]
                    cursor.execute("""
                        UPDATE conversations
                        SET updated_at = NOW()
                        WHERE id = %s AND company_id = %s
                    """, (str(conversation_id), current_user["company_id"]))
                
            # If escalation recommended, create escalation record.
            # This remains outside the response transaction because escalation
            # is advisory and must not discard an otherwise valid answer.
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
            logger.exception("Error persisting RAG result")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Answer generated but conversation could not be saved",
            ) from log_error

        result["conversation_id"] = conversation_id
        result["message_id"] = message_id
        return QueryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing query")
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
