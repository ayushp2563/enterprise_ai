import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from app.models.documents import Document
from app.services.document_ingestion import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.security.auth import get_current_user, require_hr_or_admin
from app.config import get_settings
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()


@router.post("/upload")
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
        allowed_extensions = ['pdf', 'docx', 'doc', 'txt', 'md']
        file_ext = file.filename.split('.')[-1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (10MB limit)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 10MB limit"
            )
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process document
            ingestion_service = get_ingestion_service()
            result = ingestion_service.process_document(
                file_path=tmp_file_path,
                file_type=file_ext,
                metadata={"filename": file.filename}
            )
            
            # Store in database with company context
            conn = psycopg2.connect(settings.database_url)
            cursor = conn.cursor()
            
            # Insert document
            doc_title = title or file.filename
            cursor.execute(
                """
                INSERT INTO documents 
                (company_id, uploaded_by, title, content, category, metadata, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, true, %s, %s)
                RETURNING id
                """,
                (
                    current_user["company_id"],
                    current_user["id"],
                    doc_title,
                    " ".join(result['chunks'][:3]),  # Store first few chunks as preview
                    category or "General",
                    Json({"filename": file.filename, "num_chunks": result['num_chunks']}),
                    datetime.now(),
                    datetime.now()
                )
            )
            
            document_id = cursor.fetchone()[0]
            conn.commit()
            
            # Store chunks with embeddings
            vector_store = get_vector_store()
            chunk_ids = vector_store.store_document_chunks(
                document_id=document_id,
                chunks=result['chunks'],
                embeddings=result['embeddings']
            )
            
            cursor.close()
            conn.close()
            
            logger.info(f"User {current_user['email']} uploaded document: {file.filename} (ID: {document_id})")
            
            return {
                "document_id": document_id,
                "title": doc_title,
                "category": category or "General",
                "num_chunks": result['num_chunks'],
                "status": "processed"
            }
            
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
            
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
                SELECT id, title, category, metadata, uploaded_by, created_at
                FROM documents
                WHERE company_id = %s AND category = %s AND is_active = true
                ORDER BY created_at DESC
                """,
                (current_user["company_id"], category)
            )
        else:
            cursor.execute(
                """
                SELECT id, title, category, metadata, uploaded_by, created_at
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
                "title": row[1],
                "category": row[2],
                "metadata": row[3],
                "uploaded_by": row[4],
                "created_at": row[5].isoformat()
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


@router.get("/{document_id}")
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
            SELECT id, title, category, content, metadata, uploaded_by, created_at, updated_at
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
            "title": row[1],
            "category": row[2],
            "content": row[3],
            "metadata": row[4],
            "uploaded_by": row[5],
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat()
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


@router.delete("/{document_id}")
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
            RETURNING id
            """,
            (document_id, current_user["company_id"])
        )
        
        deleted_id = cursor.fetchone()
        
        if not deleted_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
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
