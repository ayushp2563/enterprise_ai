import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from app.models.documents import Document, DocumentCreate
from app.services.document_ingestion import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.security.auth import verify_api_key
from app.config import get_settings
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Upload and process a document.
    
    Args:
        file: Document file
        title: Optional document title
        api_key: Validated API key
        
    Returns:
        Document processing result
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
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            content = await file.read()
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
            
            # Store in database
            conn = psycopg2.connect(settings.database_url)
            cursor = conn.cursor()
            
            # Insert document
            doc_title = title or file.filename
            cursor.execute(
                """
                INSERT INTO documents (title, content, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    doc_title,
                    " ".join(result['chunks'][:3]),  # Store first few chunks as preview
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
            
            logger.info(f"Successfully processed document: {file.filename}")
            
            return {
                "document_id": document_id,
                "title": doc_title,
                "num_chunks": result['num_chunks'],
                "status": "processed"
            }
            
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/")
async def list_documents(
    api_key: str = Depends(verify_api_key)
):
    """
    List all documents.
    
    Args:
        api_key: Validated API key
        
    Returns:
        List of documents
    """
    try:
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, title, metadata, created_at
            FROM documents
            ORDER BY created_at DESC
            """
        )
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                "id": row[0],
                "title": row[1],
                "metadata": row[2],
                "created_at": row[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return {"documents": documents, "count": len(documents)}
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a document and its chunks.
    
    Args:
        document_id: ID of document to delete
        api_key: Validated API key
        
    Returns:
        Deletion confirmation
    """
    try:
        # Delete chunks first
        vector_store = get_vector_store()
        vector_store.delete_document_chunks(document_id)
        
        # Delete document
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM documents WHERE id = %s RETURNING id",
            (document_id,)
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
        
        logger.info(f"Deleted document: {document_id}")
        
        return {"status": "deleted", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )
