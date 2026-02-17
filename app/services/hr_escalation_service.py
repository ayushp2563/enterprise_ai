import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HREscalationService:
    """Service for HR escalation logic and management."""
    
    # Sensitive keywords that trigger HR escalation
    SENSITIVE_KEYWORDS = [
        "discrimination", "harassment", "harass", "bully", "bullying",
        "complaint", "legal", "lawsuit", "sue", "termination", "fired",
        "salary dispute", "wage", "unpaid", "overtime",
        "hostile", "unsafe", "injury", "accident", "workers comp",
        "retaliation", "whistleblow", "ethics", "violation",
        "sexual", "assault", "abuse", "threat", "violence"
    ]
    
    # Confidence threshold for escalation
    LOW_CONFIDENCE_THRESHOLD = 0.6
    
    def __init__(self):
        """Initialize the HR escalation service."""
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(settings.database_url)
            logger.info("HREscalationService: Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"HREscalationService: Failed to connect to database: {str(e)}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.connection is None or self.connection.closed:
            self._connect()
    
    def calculate_confidence_score(
        self,
        similarity_scores: List[float],
        num_sources: int,
        answer_length: int
    ) -> float:
        """
        Calculate confidence score for a RAG response.
        
        Args:
            similarity_scores: List of similarity scores from vector search
            num_sources: Number of source documents found
            answer_length: Length of generated answer
            
        Returns:
            Confidence score between 0 and 1
        """
        if not similarity_scores or num_sources == 0:
            return 0.0
        
        # Average similarity score (weighted more heavily)
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        
        # Normalize number of sources (cap at 5)
        source_score = min(num_sources / 5.0, 1.0)
        
        # Answer length score (prefer substantial answers)
        # Penalize very short answers (< 50 chars) and very long ones (> 1000 chars)
        if answer_length < 50:
            length_score = answer_length / 50.0
        elif answer_length > 1000:
            length_score = 1000.0 / answer_length
        else:
            length_score = 1.0
        
        # Weighted combination
        confidence = (
            avg_similarity * 0.6 +  # 60% weight on similarity
            source_score * 0.3 +     # 30% weight on number of sources
            length_score * 0.1       # 10% weight on answer quality
        )
        
        return round(confidence, 3)
    
    def contains_sensitive_keywords(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Check if question contains sensitive keywords.
        
        Returns:
            Tuple of (has_sensitive_keyword, matched_keyword)
        """
        question_lower = question.lower()
        
        for keyword in self.SENSITIVE_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', question_lower):
                return True, keyword
        
        return False, None
    
    def should_escalate_to_hr(
        self,
        question: str,
        confidence_score: float,
        num_sources: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if a query should be escalated to HR.
        
        Returns:
            Tuple of (should_escalate, reason)
        """
        # Check for explicit HR request
        hr_keywords = ["contact hr", "talk to hr", "speak to hr", "hr department", "human resources"]
        question_lower = question.lower()
        for keyword in hr_keywords:
            if keyword in question_lower:
                return True, "User explicitly requested HR contact"
        
        # Check for sensitive keywords
        has_sensitive, keyword = self.contains_sensitive_keywords(question)
        if has_sensitive:
            return True, f"Sensitive topic detected: '{keyword}'"
        
        # Check for low confidence
        if confidence_score < self.LOW_CONFIDENCE_THRESHOLD:
            return True, f"Low confidence score ({confidence_score:.2f})"
        
        # Check for no relevant documents
        if num_sources == 0:
            return True, "No relevant policy documents found"
        
        return False, None
    
    def create_escalation(
        self,
        company_id: int,
        user_id: int,
        question: str,
        reason: str,
        query_log_id: Optional[int] = None
    ) -> dict:
        """Create an HR escalation record."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO hr_escalations 
                    (company_id, user_id, question, reason, query_log_id, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING id, company_id, user_id, question, reason, status, 
                              query_log_id, hr_response, resolved_by, resolved_at, created_at
                """, (company_id, user_id, question, reason, query_log_id))
                
                row = cursor.fetchone()
                escalation = {
                    "id": row[0],
                    "company_id": row[1],
                    "user_id": row[2],
                    "question": row[3],
                    "reason": row[4],
                    "status": row[5],
                    "query_log_id": row[6],
                    "hr_response": row[7],
                    "resolved_by": row[8],
                    "resolved_at": row[9],
                    "created_at": row[10]
                }
                
                self.connection.commit()
                logger.info(f"Created HR escalation {escalation['id']} for company {company_id}")
                
                return escalation
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating HR escalation: {str(e)}")
            raise
    
    def get_escalations_by_company(
        self,
        company_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """Get HR escalations for a company."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                if status:
                    query = """
                        SELECT id, company_id, user_id, question, reason, status, 
                               query_log_id, hr_response, resolved_by, resolved_at, created_at
                        FROM hr_escalations
                        WHERE company_id = %s AND status = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(query, (company_id, status, limit, skip))
                else:
                    query = """
                        SELECT id, company_id, user_id, question, reason, status, 
                               query_log_id, hr_response, resolved_by, resolved_at, created_at
                        FROM hr_escalations
                        WHERE company_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(query, (company_id, limit, skip))
                
                escalations = []
                for row in cursor.fetchall():
                    escalations.append({
                        "id": row[0],
                        "company_id": row[1],
                        "user_id": row[2],
                        "question": row[3],
                        "reason": row[4],
                        "status": row[5],
                        "query_log_id": row[6],
                        "hr_response": row[7],
                        "resolved_by": row[8],
                        "resolved_at": row[9],
                        "created_at": row[10]
                    })
                
                return escalations
                
        except Exception as e:
            logger.error(f"Error getting HR escalations: {str(e)}")
            raise
    
    def respond_to_escalation(
        self,
        escalation_id: int,
        company_id: int,
        hr_response: str,
        resolved_by: int
    ) -> Optional[dict]:
        """Respond to an HR escalation."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE hr_escalations
                    SET hr_response = %s, resolved_by = %s, resolved_at = NOW(), status = 'resolved'
                    WHERE id = %s AND company_id = %s
                    RETURNING id, company_id, user_id, question, reason, status, 
                              query_log_id, hr_response, resolved_by, resolved_at, created_at
                """, (hr_response, resolved_by, escalation_id, company_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                escalation = {
                    "id": row[0],
                    "company_id": row[1],
                    "user_id": row[2],
                    "question": row[3],
                    "reason": row[4],
                    "status": row[5],
                    "query_log_id": row[6],
                    "hr_response": row[7],
                    "resolved_by": row[8],
                    "resolved_at": row[9],
                    "created_at": row[10]
                }
                
                self.connection.commit()
                logger.info(f"Resolved HR escalation {escalation_id}")
                
                return escalation
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error responding to HR escalation: {str(e)}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Closed HREscalationService database connection")


# Singleton instance
_hr_escalation_service = None


def get_hr_escalation_service() -> HREscalationService:
    """Get singleton instance of HREscalationService."""
    global _hr_escalation_service
    if _hr_escalation_service is None:
        _hr_escalation_service = HREscalationService()
    return _hr_escalation_service
