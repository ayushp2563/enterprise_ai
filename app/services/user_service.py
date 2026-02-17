import logging
from typing import List, Optional
import psycopg2
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserService:
    """Service for user management operations."""
    
    def __init__(self):
        """Initialize the user service."""
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(settings.database_url)
            logger.info("UserService: Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"UserService: Failed to connect to database: {str(e)}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.connection is None or self.connection.closed:
            self._connect()
    
    def get_users_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get all users for a company."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, company_id, email, full_name, role, is_active, 
                           last_login, created_at, updated_at
                    FROM users
                    WHERE company_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (company_id, limit, skip))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        "id": row[0],
                        "company_id": row[1],
                        "email": row[2],
                        "full_name": row[3],
                        "role": row[4],
                        "is_active": row[5],
                        "last_login": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            raise
    
    def get_user_by_id(self, user_id: int, company_id: int) -> Optional[dict]:
        """Get user by ID (with company isolation)."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, company_id, email, full_name, role, is_active, 
                           last_login, created_at, updated_at
                    FROM users
                    WHERE id = %s AND company_id = %s
                """, (user_id, company_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "role": row[4],
                    "is_active": row[5],
                    "last_login": row[6],
                    "created_at": row[7],
                    "updated_at": row[8]
                }
                
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise
    
    def update_user(
        self,
        user_id: int,
        company_id: int,
        full_name: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[dict]:
        """Update user details (with company isolation)."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Build dynamic update query
                updates = []
                params = []
                
                if full_name is not None:
                    updates.append("full_name = %s")
                    params.append(full_name)
                
                if role is not None:
                    updates.append("role = %s")
                    params.append(role)
                
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)
                
                if not updates:
                    # No updates to make
                    return self.get_user_by_id(user_id, company_id)
                
                params.extend([user_id, company_id])
                
                query = f"""
                    UPDATE users
                    SET {', '.join(updates)}
                    WHERE id = %s AND company_id = %s
                    RETURNING id, company_id, email, full_name, role, is_active, 
                              last_login, created_at, updated_at
                """
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                user = {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "role": row[4],
                    "is_active": row[5],
                    "last_login": row[6],
                    "created_at": row[7],
                    "updated_at": row[8]
                }
                
                self.connection.commit()
                logger.info(f"Updated user {user_id}")
                
                return user
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating user: {str(e)}")
            raise
    
    def deactivate_user(self, user_id: int, company_id: int) -> bool:
        """Deactivate a user (soft delete with company isolation)."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET is_active = false
                    WHERE id = %s AND company_id = %s
                """, (user_id, company_id))
                
                affected = cursor.rowcount
                self.connection.commit()
                
                if affected > 0:
                    logger.info(f"Deactivated user {user_id}")
                    return True
                return False
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deactivating user: {str(e)}")
            raise
    
    def get_invitations_by_company(self, company_id: int) -> List[dict]:
        """Get all pending invitations for a company."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, company_id, email, role, token, invited_by, 
                           expires_at, accepted_at, created_at
                    FROM invitations
                    WHERE company_id = %s AND accepted_at IS NULL
                    ORDER BY created_at DESC
                """, (company_id,))
                
                invitations = []
                for row in cursor.fetchall():
                    invitations.append({
                        "id": row[0],
                        "company_id": row[1],
                        "email": row[2],
                        "role": row[3],
                        "token": row[4],
                        "invited_by": row[5],
                        "expires_at": row[6],
                        "accepted_at": row[7],
                        "created_at": row[8]
                    })
                
                return invitations
                
        except Exception as e:
            logger.error(f"Error getting invitations: {str(e)}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Closed UserService database connection")


# Singleton instance
_user_service = None


def get_user_service() -> UserService:
    """Get singleton instance of UserService."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
