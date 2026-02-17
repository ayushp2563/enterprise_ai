import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    """Service for managing vector storage in PostgreSQL with pgvector."""
    
    def __init__(self):
        """Initialize the vector store service."""
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            # Parse database URL
            db_url = settings.database_url.replace('postgresql://', '')
            self.connection = psycopg2.connect(settings.database_url)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.connection is None or self.connection.closed:
            self._connect()
    
    def store_document_chunks(
        self,
        document_id: int,
        chunks: List[str],
        embeddings: List[List[float]]
    ) -> List[int]:
        """
        Store document chunks with their embeddings.
        
        Args:
            document_id: ID of the parent document
            chunks: List of text chunks
            embeddings: List of embedding vectors
            
        Returns:
            List of chunk IDs
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Prepare data for batch insert
                data = [
                    (document_id, chunk, idx, embedding)
                    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
                ]
                
                # Batch insert chunks
                query = """
                    INSERT INTO document_chunks (document_id, chunk_text, chunk_index, embedding)
                    VALUES %s
                    RETURNING id
                """
                
                chunk_ids = execute_values(
                    cursor,
                    query,
                    data,
                    template="(%s, %s, %s, %s::vector)",
                    fetch=True
                )
                
                self.connection.commit()
                logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
                
                return [row[0] for row in chunk_ids]
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error storing document chunks: {str(e)}")
            raise
    
    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = -1.0
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using cosine distance.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar chunks with metadata
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT 
                        dc.id,
                        dc.document_id,
                        dc.chunk_text,
                        dc.chunk_index,
                        d.title,
                        d.metadata,
                        1 - (dc.embedding <=> %s::vector) as similarity
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    ORDER BY dc.embedding <=> %s::vector
                    LIMIT %s
                """
                
                cursor.execute(
                    query,
                    (query_embedding, query_embedding, top_k)
                )
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "chunk_text": row[2],
                        "chunk_index": row[3],
                        "document_title": row[4],
                        "metadata": row[5],
                        "similarity": float(row[6])
                    })
                
                logger.info(f"Found {len(results)} similar chunks")
                return results
                
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise
    
    def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of chunks
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                query = """
                    SELECT id, chunk_text, chunk_index
                    FROM document_chunks
                    WHERE document_id = %s
                    ORDER BY chunk_index
                """
                
                cursor.execute(query, (document_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "id": row[0],
                        "chunk_text": row[1],
                        "chunk_index": row[2]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            raise
    
    def delete_document_chunks(self, document_id: int):
        """
        Delete all chunks for a document.
        
        Args:
            document_id: ID of the document
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM document_chunks WHERE document_id = %s",
                    (document_id,)
                )
                self.connection.commit()
                logger.info(f"Deleted chunks for document {document_id}")
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deleting document chunks: {str(e)}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Closed database connection")


# Singleton instance
_vector_store = None


def get_vector_store() -> VectorStoreService:
    """Get singleton instance of VectorStoreService."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
