from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowType(str, Enum):
    """Workflow types."""
    TICKET_CREATION = "ticket_creation"
    REPORT_SUMMARY = "report_summary"
    CUSTOM = "custom"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRequest(BaseModel):
    """Workflow execution request."""
    workflow_type: WorkflowType
    parameters: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow execution response."""
    workflow_id: int
    status: WorkflowStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TicketCreationParams(BaseModel):
    """Parameters for ticket creation workflow."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    category: Optional[str] = None


class ReportSummaryParams(BaseModel):
    """Parameters for report summary workflow."""
    report_text: str = Field(..., min_length=1)
    max_length: Optional[int] = Field(default=500, ge=100, le=2000)
