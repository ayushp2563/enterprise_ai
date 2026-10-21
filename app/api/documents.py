import logging
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import psycopg2
from psycopg2.extras import Json
from app.services.document_storage import get_document_storage
from app.services.vector_store import get_vector_store
from app.security.auth import get_current_user, require_hr_or_admin
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: dict = Depends(require_hr_or_admin)
):
    """
    Upload and process a company policy document.
    
    Requires: HR Manager or Admin role
    """
    try:
        # Validate file type
        allowed_extensions = {
            "pdf": {"application/pdf"},
            "docx": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
            "txt": {"text/plain", "application/octet-stream"},
            "md": {"text/markdown", "text/plain", "application/octet-stream"},
        }
        filename = file.filename or "document"
        file_ext = filename.rsplit('.', 1)[-1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        if file.content_type and file.content_type not in allowed_extensions[file_ext]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Declared media type does not match the supported document type",
            )

        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded document is empty",
            )
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds configured upload limit"
            )

        checksum = hashlib.sha256(content).hexdigest()
        storage = get_document_storage()
        storage_key = storage.save(current_user["company_id"], file_ext, content)
        conn = None
        try:
            conn = psycopg2.connect(settings.database_url)
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id
                        FROM documents
                        WHERE company_id = %s
                          AND checksum_sha256 = %s
                          AND is_active = true
                    """, (current_user["company_id"], checksum))
                    if cursor.fetchone():
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="This document has already been uploaded",
                        )

                    doc_title = title or filename
                    cursor.execute("""
                        INSERT INTO documents (
                            company_id, uploaded_by, title, content, category,
                            metadata, is_active, original_filename, media_type,
                            storage_key, checksum_sha256, ingestion_status
                        )
                        VALUES (
                            %s, %s, %s, NULL, %s, %s, true, %s, %s, %s, %s,
                            'pending'
                        )
                        RETURNING id, public_id
                    """, (
                        current_user["company_id"],
                        current_user["id"],
                        doc_title,
                        category or "General",
                        Json({"filename": filename, "size_bytes": len(content)}),
                        filename,
                        file.content_type,
                        storage_key,
                        checksum,
                    ))
                    document_id, public_id = cursor.fetchone()

                    cursor.execute("""
                        INSERT INTO ingestion_jobs (
                            company_id, document_id, status, max_attempts
                        )
                        VALUES (%s, %s, 'pending', %s)
                    """, (
                        current_user["company_id"],
                        document_id,
                        settings.ingestion_max_attempts,
                    ))

            logger.info(
                "Document accepted for ingestion",
                extra={
                    "company_id": current_user["company_id"],
                    "document_id": document_id,
                },
            )

            return {
                "document_id": document_id,
                "public_id": str(public_id),
                "title": doc_title,
                "category": category or "General",
                "status": "pending",
            }
        except Exception:
            storage.delete(storage_key)
            raise
        finally:
            if conn is not None:
                conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing document"
        )


@router.get("/", response_model=dict)
async def list_documents(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List all documents for the company.
    
    Requires: Authentication (any role)
    """
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        if category:
            cursor.execute(
                """
                SELECT id, public_id, title, category, metadata, uploaded_by,
                       original_filename, media_type, ingestion_status,
                       ingestion_error, created_at
                FROM documents
                WHERE company_id = %s AND category = %s AND is_active = true
                ORDER BY created_at DESC
                """,
                (current_user["company_id"], category)
            )
        else:
            cursor.execute(
                """
                SELECT id, public_id, title, category, metadata, uploaded_by,
                       original_filename, media_type, ingestion_status,
                       ingestion_error, created_at
                FROM documents
                WHERE company_id = %s AND is_active = true
                ORDER BY created_at DESC
                """,
                (current_user["company_id"],)
            )
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                "id": row[0],
                "public_id": str(row[1]),
                "title": row[2],
                "category": row[3],
                "metadata": row[4],
                "uploaded_by": row[5],
                "original_filename": row[6],
                "media_type": row[7],
                "ingestion_status": row[8],
                "ingestion_error": row[9],
                "created_at": row[10].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return {"documents": documents, "count": len(documents)}
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing documents"
        )


@router.get("/{document_id:int}")
async def get_document(
    document_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get document details.
    
    Requires: Authentication (any role)
    """
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, public_id, title, category, content, metadata,
                   uploaded_by, original_filename, media_type,
                   ingestion_status, ingestion_error, created_at, updated_at
            FROM documents
            WHERE id = %s AND company_id = %s AND is_active = true
            """,
            (document_id, current_user["company_id"])
        )
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        document = {
            "id": row[0],
            "public_id": str(row[1]),
            "title": row[2],
            "category": row[3],
            "content": row[4],
            "metadata": row[5],
            "uploaded_by": row[6],
            "original_filename": row[7],
            "media_type": row[8],
            "ingestion_status": row[9],
            "ingestion_error": row[10],
            "created_at": row[11].isoformat(),
            "updated_at": row[12].isoformat()
        }
        
        cursor.close()
        conn.close()
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document"
        )


@router.delete("/{document_id:int}")
async def delete_document(
    document_id: int,
    current_user: dict = Depends(require_hr_or_admin)
):
    """
    Delete a document (soft delete).
    
    Requires: HR Manager or Admin role
    """
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        # Soft delete (mark as inactive)
        cursor.execute(
            """
            UPDATE documents 
            SET is_active = false 
            WHERE id = %s AND company_id = %s
            RETURNING id, storage_key
            """,
            (document_id, current_user["company_id"])
        )
        
        deleted = cursor.fetchone()
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        cursor.execute("""
            UPDATE ingestion_jobs
            SET status = 'failed',
                completed_at = NOW(),
                error_code = 'document_deleted',
                error_detail = 'Document was deleted'
            WHERE document_id = %s
              AND status IN ('pending', 'processing')
        """, (document_id,))
        conn.commit()
        cursor.close()
        conn.close()

        get_vector_store().delete_document_chunks(
            document_id,
            current_user["company_id"],
        )
        get_document_storage().delete(deleted[1])
        
        logger.info(f"User {current_user['email']} deleted document: {document_id}")
        
        return {"status": "deleted", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document"
        )


@router.get("/categories/list")
async def list_categories(
    current_user: dict = Depends(get_current_user)
):
    """
    List all document categories for the company.
    
    Requires: Authentication (any role)
    """
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT DISTINCT category, COUNT(*) as count
            FROM documents
            WHERE company_id = %s AND is_active = true
            GROUP BY category
            ORDER BY category
            """,
            (current_user["company_id"],)
        )
        
        categories = [{"name": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {"categories": categories}
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing categories"
        )
