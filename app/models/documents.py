from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document model."""
    title: str
    content: str
    metadata: Optional[dict] = None


class DocumentCreate(DocumentBase):
    """Document creation model."""
    pass


class Document(DocumentBase):
    """Document model with ID and timestamps."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    """Document chunk with embedding."""
    id: int
    document_id: int
    chunk_text: str
    chunk_index: int
    embedding: Optional[List[float]] = None
    
    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    """Query request model."""
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    """Query response model."""
    answer: str
    sources: List[dict]
    query_time: float
    model_used: str


class QueryLog(BaseModel):
    """Query log model."""
    id: int
    question: str
    answer: str
    sources: dict
    created_at: datetime
    
    class Config:
        from_attributes = True
