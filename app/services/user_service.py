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

    @staticmethod
    def _guard_last_owner(cursor, user_id: int, company_id: int) -> None:
        """Prevent removal or demotion of the final active owner."""
        # Serialize owner-count changes for one organization. The advisory lock
        # is released automatically when the surrounding transaction ends.
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (company_id,)
        )
        cursor.execute("""
            SELECT role, is_active
            FROM memberships
            WHERE user_id = %s AND company_id = %s
        """, (user_id, company_id))
        target = cursor.fetchone()
        if not target or target[0] != "owner" or not target[1]:
            return

        cursor.execute("""
            SELECT COUNT(*)
            FROM memberships
            WHERE company_id = %s
              AND role = 'owner'
              AND is_active = true
        """, (company_id,))
        if cursor.fetchone()[0] <= 1:
            raise ValueError("The organization must retain at least one active owner")
    
    def get_users_by_company(self, company_id: int, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get all users for a company."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        u.id, u.public_id, m.company_id, u.email, u.full_name,
                        m.id, m.role, (u.is_active AND m.is_active),
                        u.last_login, u.created_at, u.updated_at
                    FROM memberships AS m
                    JOIN users AS u ON u.id = m.user_id
                    WHERE m.company_id = %s
                    ORDER BY m.created_at DESC
                    LIMIT %s OFFSET %s
                """, (company_id, limit, skip))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        "id": row[0],
                        "public_id": row[1],
                        "company_id": row[2],
                        "email": row[3],
                        "full_name": row[4],
                        "membership_id": row[5],
                        "role": row[6],
                        "is_active": row[7],
                        "last_login": row[8],
                        "created_at": row[9],
                        "updated_at": row[10]
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
                    SELECT
                        u.id, u.public_id, m.company_id, u.email, u.full_name,
                        m.id, m.role, (u.is_active AND m.is_active),
                        u.last_login, u.created_at, u.updated_at
                    FROM memberships AS m
                    JOIN users AS u ON u.id = m.user_id
                    WHERE u.id = %s AND m.company_id = %s
                """, (user_id, company_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "public_id": row[1],
                    "company_id": row[2],
                    "email": row[3],
                    "full_name": row[4],
                    "membership_id": row[5],
                    "role": row[6],
                    "is_active": row[7],
                    "last_login": row[8],
                    "created_at": row[9],
                    "updated_at": row[10]
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
                if (role is not None and role != "owner") or is_active is False:
                    self._guard_last_owner(cursor, user_id, company_id)

                if full_name is not None:
                    cursor.execute("""
                        UPDATE users AS u
                        SET full_name = %s
                        FROM memberships AS m
                        WHERE u.id = %s
                          AND m.user_id = u.id
                          AND m.company_id = %s
                    """, (full_name, user_id, company_id))

                membership_updates = []
                membership_params = []
                if role is not None:
                    membership_updates.append("role = %s")
                    membership_params.append(role)
                if is_active is not None:
                    membership_updates.append("is_active = %s")
                    membership_params.append(is_active)

                if membership_updates:
                    membership_params.extend([user_id, company_id])
                    cursor.execute(f"""
                        UPDATE memberships
                        SET {', '.join(membership_updates)}
                        WHERE user_id = %s AND company_id = %s
                    """, membership_params)

                cursor.execute("""
                    SELECT 1
                    FROM memberships
                    WHERE user_id = %s AND company_id = %s
                """, (user_id, company_id))
                if not cursor.fetchone():
                    self.connection.rollback()
                    return None

                self.connection.commit()
                logger.info(f"Updated user {user_id}")
                return self.get_user_by_id(user_id, company_id)
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating user: {str(e)}")
            raise
    
    def deactivate_user(self, user_id: int, company_id: int) -> bool:
        """Deactivate a user (soft delete with company isolation)."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                self._guard_last_owner(cursor, user_id, company_id)
                cursor.execute("""
                    UPDATE memberships
                    SET is_active = false
                    WHERE user_id = %s AND company_id = %s
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
                    SELECT id, company_id, email, role, invited_by,
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
                        "invited_by": row[4],
                        "expires_at": row[5],
                        "accepted_at": row[6],
                        "created_at": row[7]
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
