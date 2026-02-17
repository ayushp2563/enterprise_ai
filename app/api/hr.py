import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.documents import HREscalationResponse, HREscalationUpdate
from app.services.hr_escalation_service import get_hr_escalation_service, HREscalationService
from app.security.auth import get_current_user, require_hr_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hr", tags=["HR"])


@router.get("/escalations", response_model=List[dict])
async def list_escalations(
    status_filter: str = Query(None, description="Filter by status: pending, contacted, resolved"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_hr_or_admin),
    hr_service: HREscalationService = Depends(get_hr_escalation_service)
):
    """
    List HR escalations for the company.
    
    Requires: HR Manager or Admin role
    """
    try:
        escalations = hr_service.get_escalations_by_company(
            company_id=current_user["company_id"],
            status=status_filter,
            skip=skip,
            limit=limit
        )
        return escalations
        
    except Exception as e:
        logger.error(f"Error listing escalations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list escalations"
        )


@router.post("/escalations/{escalation_id}/respond")
async def respond_to_escalation(
    escalation_id: int,
    response: str,
    current_user: dict = Depends(require_hr_or_admin),
    hr_service: HREscalationService = Depends(get_hr_escalation_service)
):
    """
    Respond to an HR escalation and mark it as resolved.
    
    Requires: HR Manager or Admin role
    """
    try:
        escalation = hr_service.respond_to_escalation(
            escalation_id=escalation_id,
            company_id=current_user["company_id"],
            hr_response=response,
            resolved_by=current_user["id"]
        )
        
        if not escalation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Escalation not found"
            )
        
        logger.info(f"Escalation {escalation_id} resolved by {current_user['email']}")
        return escalation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error responding to escalation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to escalation"
        )


@router.get("/analytics")
async def get_hr_analytics(
    current_user: dict = Depends(require_hr_or_admin)
):
    """
    Get HR analytics and statistics.
    
    Requires: HR Manager or Admin role
    """
    try:
        import psycopg2
        from app.config import get_settings
        settings = get_settings()
        
        connection = psycopg2.connect(settings.database_url)
        with connection.cursor() as cursor:
            # Total escalations
            cursor.execute("""
                SELECT COUNT(*) FROM hr_escalations
                WHERE company_id = %s
            """, (current_user["company_id"],))
            total_escalations = cursor.fetchone()[0]
            
            # Pending escalations
            cursor.execute("""
                SELECT COUNT(*) FROM hr_escalations
                WHERE company_id = %s AND status = 'pending'
            """, (current_user["company_id"],))
            pending_escalations = cursor.fetchone()[0]
            
            # Average confidence score
            cursor.execute("""
                SELECT AVG(confidence_score) FROM query_logs
                WHERE company_id = %s AND confidence_score IS NOT NULL
            """, (current_user["company_id"],))
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # Total queries
            cursor.execute("""
                SELECT COUNT(*) FROM query_logs
                WHERE company_id = %s
            """, (current_user["company_id"],))
            total_queries = cursor.fetchone()[0]
            
            # Escalation rate
            cursor.execute("""
                SELECT COUNT(*) FROM query_logs
                WHERE company_id = %s AND escalated_to_hr = true
            """, (current_user["company_id"],))
            escalated_queries = cursor.fetchone()[0]
            
            escalation_rate = (escalated_queries / total_queries * 100) if total_queries > 0 else 0.0
            
            # Top escalation reasons
            cursor.execute("""
                SELECT reason, COUNT(*) as count
                FROM hr_escalations
                WHERE company_id = %s
                GROUP BY reason
                ORDER BY count DESC
                LIMIT 5
            """, (current_user["company_id"],))
            top_reasons = [{"reason": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        connection.close()
        
        return {
            "total_escalations": total_escalations,
            "pending_escalations": pending_escalations,
            "total_queries": total_queries,
            "escalation_rate": round(escalation_rate, 2),
            "average_confidence_score": round(float(avg_confidence), 3),
            "top_escalation_reasons": top_reasons
        }
        
    except Exception as e:
        logger.error(f"Error getting HR analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )
