"""Tenant-scoped conversation history endpoints."""

from uuid import UUID

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import get_settings
from app.security.auth import get_current_user


router = APIRouter(prefix="/api/conversations", tags=["Conversations"])
settings = get_settings()


@router.get("/")
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    connection = psycopg2.connect(settings.database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE company_id = %s
                  AND user_id = %s
                  AND archived_at IS NULL
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
            """, (
                current_user["company_id"],
                current_user["id"],
                limit,
                offset,
            ))
            items = [{
                "id": str(row[0]),
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
            } for row in cursor.fetchall()]
        return {"conversations": items, "limit": limit, "offset": offset}
    finally:
        connection.close()


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    connection = psycopg2.connect(settings.database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = %s
                  AND company_id = %s
                  AND user_id = %s
                  AND archived_at IS NULL
            """, (
                str(conversation_id),
                current_user["company_id"],
                current_user["id"],
            ))
            conversation = cursor.fetchone()
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )

            cursor.execute("""
                SELECT id, role, content, citations, retrieval_metadata,
                       model, created_at
                FROM messages
                WHERE conversation_id = %s
                  AND company_id = %s
                ORDER BY created_at, id
            """, (str(conversation_id), current_user["company_id"]))
            messages = [{
                "id": str(row[0]),
                "role": row[1],
                "content": row[2],
                "citations": row[3],
                "retrieval_metadata": row[4],
                "model": row[5],
                "created_at": row[6],
            } for row in cursor.fetchall()]

        return {
            "id": str(conversation[0]),
            "title": conversation[1],
            "created_at": conversation[2],
            "updated_at": conversation[3],
            "messages": messages,
        }
    finally:
        connection.close()
