from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document model."""
    title: str
    content: str
    category: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentCreate(DocumentBase):
    """Document creation model."""
    pass


class Document(DocumentBase):
    """Document model with ID and timestamps."""
    id: int
    company_id: int
    uploaded_by: Optional[int] = None
    is_active: bool
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
    confidence_score: float
    should_escalate: bool
    escalation_reason: Optional[str] = None
    hr_contact: Optional[dict] = None


class QueryLog(BaseModel):
    """Query log model."""
    id: int
    question: str
    answer: str
    sources: dict
    query_time: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class HREscalationResponse(BaseModel):
    """HR escalation response model."""
    id: int
    company_id: int
    user_id: int
    question: str
    reason: str
    status: str
    query_log_id: Optional[int] = None
    hr_response: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class HREscalationUpdate(BaseModel):
    """HR escalation update model."""
    response: str
    
    class Config:
        from_attributes = True
