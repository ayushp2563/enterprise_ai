import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import psycopg2
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# # Password hashing context
# pwd_context = CryptContext(
#     schemes=["bcrypt"],
#     deprecated="auto",
#     bcrypt__ident="2b",
#     bcrypt__truncate_error=False  # Allow automatic truncation for passwords > 72 bytes
# )

# Line 14 in auth_service.py
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(self):
        """Initialize the auth service."""
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(settings.database_url)
            logger.info("AuthService: Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"AuthService: Failed to connect to database: {str(e)}")
            raise
    
    def _ensure_connection(self):
        """Ensure database connection is active."""
        if self.connection is None or self.connection.closed:
            self._connect()
    
    # ========================================================================
    # Password Hashing
    # ========================================================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        # Bcrypt has a 72-byte limit - truncate password if necessary
        # This prevents passlib from raising an error
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        safe_password = password_bytes.decode('utf-8', errors='ignore')
        return pwd_context.hash(safe_password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # Truncate password to match hashing behavior
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        safe_password = password_bytes.decode('utf-8', errors='ignore')
        return pwd_context.verify(safe_password, hashed_password)
    
    # ========================================================================
    # JWT Token Management
    # ========================================================================
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            return None
    
    # ========================================================================
    # Company Management
    # ========================================================================
    
    def create_company(
        self,
        name: str,
        slug: str,
        domain: Optional[str],
        admin_email: str,
        admin_password: str,
        admin_full_name: str
    ) -> Tuple[dict, dict]:
        """
        Create a new company with an admin user.
        
        Returns:
            Tuple of (company_dict, user_dict)
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Check if slug already exists
                cursor.execute("SELECT id FROM companies WHERE slug = %s", (slug,))
                if cursor.fetchone():
                    raise ValueError(f"Company with slug '{slug}' already exists")
                
                # Check if email already exists
                cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
                if cursor.fetchone():
                    raise ValueError(f"User with email '{admin_email}' already exists")
                
                # Create company
                cursor.execute("""
                    INSERT INTO companies (name, slug, domain, is_active)
                    VALUES (%s, %s, %s, true)
                    RETURNING id, name, slug, domain, settings, subscription_tier, 
                              max_employees, max_documents, is_active, created_at, updated_at
                """, (name, slug, domain))
                
                company_row = cursor.fetchone()
                company = {
                    "id": company_row[0],
                    "name": company_row[1],
                    "slug": company_row[2],
                    "domain": company_row[3],
                    "settings": company_row[4],
                    "subscription_tier": company_row[5],
                    "max_employees": company_row[6],
                    "max_documents": company_row[7],
                    "is_active": company_row[8],
                    "created_at": company_row[9],
                    "updated_at": company_row[10]
                }
                
                # Create admin user
                password_hash = self.hash_password(admin_password)
                cursor.execute("""
                    INSERT INTO users (company_id, email, password_hash, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, 'company_admin', true)
                    RETURNING id, company_id, email, full_name, role, is_active, 
                              last_login, created_at, updated_at
                """, (company["id"], admin_email, password_hash, admin_full_name))
                
                user_row = cursor.fetchone()
                user = {
                    "id": user_row[0],
                    "company_id": user_row[1],
                    "email": user_row[2],
                    "full_name": user_row[3],
                    "role": user_row[4],
                    "is_active": user_row[5],
                    "last_login": user_row[6],
                    "created_at": user_row[7],
                    "updated_at": user_row[8]
                }
                
                self.connection.commit()
                logger.info(f"Created company '{name}' with admin user '{admin_email}'")
                
                return company, user
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating company: {str(e)}")
            raise
    
    def get_company_by_id(self, company_id: int) -> Optional[dict]:
        """Get company by ID."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, slug, domain, settings, subscription_tier, 
                           max_employees, max_documents, is_active, created_at, updated_at
                    FROM companies
                    WHERE id = %s
                """, (company_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "name": row[1],
                    "slug": row[2],
                    "domain": row[3],
                    "settings": row[4],
                    "subscription_tier": row[5],
                    "max_employees": row[6],
                    "max_documents": row[7],
                    "is_active": row[8],
                    "created_at": row[9],
                    "updated_at": row[10]
                }
                
        except Exception as e:
            logger.error(f"Error getting company: {str(e)}")
            raise
    
    # ========================================================================
    # User Authentication
    # ========================================================================
    
    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """
        Authenticate a user by email and password.
        
        Returns:
            User dict if authentication successful, None otherwise
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, company_id, email, password_hash, full_name, role, 
                           is_active, last_login, created_at, updated_at
                    FROM users
                    WHERE email = %s
                """, (email,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Authentication failed: User '{email}' not found")
                    return None
                
                user = {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "password_hash": row[3],
                    "full_name": row[4],
                    "role": row[5],
                    "is_active": row[6],
                    "last_login": row[7],
                    "created_at": row[8],
                    "updated_at": row[9]
                }
                
                # Check if user is active
                if not user["is_active"]:
                    logger.warning(f"Authentication failed: User '{email}' is inactive")
                    return None
                
                # Verify password
                if not self.verify_password(password, user["password_hash"]):
                    logger.warning(f"Authentication failed: Invalid password for '{email}'")
                    return None
                
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = NOW() WHERE id = %s
                """, (user["id"],))
                self.connection.commit()
                
                # Remove password hash from returned user
                del user["password_hash"]
                user["last_login"] = datetime.utcnow()
                
                logger.info(f"User '{email}' authenticated successfully")
                return user
                
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise
    
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by ID."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, company_id, email, full_name, role, is_active, 
                           last_login, created_at, updated_at
                    FROM users
                    WHERE id = %s
                """, (user_id,))
                
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
    
    # ========================================================================
    # Invitation Management
    # ========================================================================
    
    def create_invitation(
        self,
        company_id: int,
        email: str,
        role: str,
        invited_by: int
    ) -> dict:
        """Create an invitation for a new user."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Check if user already exists
                cursor.execute("""
                    SELECT id FROM users WHERE company_id = %s AND email = %s
                """, (company_id, email))
                if cursor.fetchone():
                    raise ValueError(f"User with email '{email}' already exists in this company")
                
                # Check if invitation already exists
                cursor.execute("""
                    SELECT id FROM invitations 
                    WHERE company_id = %s AND email = %s AND accepted_at IS NULL
                """, (company_id, email))
                if cursor.fetchone():
                    raise ValueError(f"Pending invitation for '{email}' already exists")
                
                # Generate token
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(days=7)
                
                # Create invitation
                cursor.execute("""
                    INSERT INTO invitations (company_id, email, role, token, invited_by, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, company_id, email, role, token, invited_by, expires_at, 
                              accepted_at, created_at
                """, (company_id, email, role, token, invited_by, expires_at))
                
                row = cursor.fetchone()
                invitation = {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "role": row[3],
                    "token": row[4],
                    "invited_by": row[5],
                    "expires_at": row[6],
                    "accepted_at": row[7],
                    "created_at": row[8]
                }
                
                self.connection.commit()
                logger.info(f"Created invitation for '{email}' to company {company_id}")
                
                return invitation
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating invitation: {str(e)}")
            raise
    
    def accept_invitation(
        self,
        token: str,
        password: str,
        full_name: str
    ) -> Tuple[dict, dict]:
        """
        Accept an invitation and create a user account.
        
        Returns:
            Tuple of (user_dict, company_dict)
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                # Get invitation
                cursor.execute("""
                    SELECT id, company_id, email, role, expires_at, accepted_at
                    FROM invitations
                    WHERE token = %s
                """, (token,))
                
                row = cursor.fetchone()
                if not row:
                    raise ValueError("Invalid invitation token")
                
                invitation = {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "role": row[3],
                    "expires_at": row[4],
                    "accepted_at": row[5]
                }
                
                # Check if already accepted
                if invitation["accepted_at"]:
                    raise ValueError("Invitation has already been accepted")
                
                # Check if expired
                if invitation["expires_at"] < datetime.utcnow():
                    raise ValueError("Invitation has expired")
                
                # Create user
                password_hash = self.hash_password(password)
                cursor.execute("""
                    INSERT INTO users (company_id, email, password_hash, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, %s, true)
                    RETURNING id, company_id, email, full_name, role, is_active, 
                              last_login, created_at, updated_at
                """, (invitation["company_id"], invitation["email"], password_hash, 
                      full_name, invitation["role"]))
                
                user_row = cursor.fetchone()
                user = {
                    "id": user_row[0],
                    "company_id": user_row[1],
                    "email": user_row[2],
                    "full_name": user_row[3],
                    "role": user_row[4],
                    "is_active": user_row[5],
                    "last_login": user_row[6],
                    "created_at": user_row[7],
                    "updated_at": user_row[8]
                }
                
                # Mark invitation as accepted
                cursor.execute("""
                    UPDATE invitations SET accepted_at = NOW() WHERE id = %s
                """, (invitation["id"],))
                
                # Get company
                company = self.get_company_by_id(invitation["company_id"])
                
                self.connection.commit()
                logger.info(f"User '{invitation['email']}' accepted invitation and created account")
                
                return user, company
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error accepting invitation: {str(e)}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Closed AuthService database connection")


# Singleton instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get singleton instance of AuthService."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
