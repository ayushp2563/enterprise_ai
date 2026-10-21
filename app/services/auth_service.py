import logging
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID, uuid4
import psycopg2
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(self):
        """Initialize lazily so unauthenticated rejection never requires DB I/O."""
        self.connection = None
    
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
        """Hash the complete password using Argon2."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    # ========================================================================
    # JWT Token Management
    # ========================================================================
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        now = datetime.now(timezone.utc)
        to_encode = data.copy()
        expire = now + (
            expires_delta
            or timedelta(minutes=settings.access_token_expire_minutes)
        )
        to_encode.update({
            "aud": settings.jwt_audience,
            "exp": expire,
            "iat": now,
            "iss": settings.jwt_issuer,
            "jti": str(uuid4()),
            "nbf": now,
            "type": "access",
        })
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate an access token."""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
            )
            return payload
        except JWTError:
            logger.info("Access token validation failed")
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
                normalized_email = admin_email.strip().lower()
                cursor.execute("SELECT id FROM users WHERE email = %s", (normalized_email,))
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
                    RETURNING id, public_id, company_id, email, full_name,
                              is_active, last_login, created_at, updated_at
                """, (company["id"], normalized_email, password_hash, admin_full_name))
                
                user_row = cursor.fetchone()

                cursor.execute("""
                    INSERT INTO memberships (company_id, user_id, role, is_active)
                    VALUES (%s, %s, 'owner', true)
                    RETURNING id
                """, (company["id"], user_row[0]))
                membership_id = cursor.fetchone()[0]

                user = {
                    "id": user_row[0],
                    "public_id": user_row[1],
                    "company_id": user_row[2],
                    "email": user_row[3],
                    "full_name": user_row[4],
                    "membership_id": membership_id,
                    "role": "owner",
                    "is_active": user_row[5],
                    "last_login": user_row[6],
                    "created_at": user_row[7],
                    "updated_at": user_row[8]
                }
                
                self.connection.commit()
                logger.info("Created organization and owner account")
                
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
    
    def authenticate_user(
        self,
        email: str,
        password: str,
        organization_slug: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Authenticate a user by email and password.
        
        Returns:
            User dict if authentication successful, None otherwise
        """
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, password_hash, is_active
                    FROM users
                    WHERE email = %s
                """, (email.strip().lower(),))
                
                row = cursor.fetchone()
                if not row:
                    return None

                user_id, password_hash, is_active = row
                if not is_active:
                    return None

                if not self.verify_password(password, password_hash):
                    return None

                params = [user_id]
                organization_filter = ""
                if organization_slug:
                    organization_filter = "AND c.slug = %s"
                    params.append(organization_slug)

                cursor.execute("""
                    SELECT m.id
                    FROM memberships AS m
                    JOIN companies AS c ON c.id = m.company_id
                    WHERE m.user_id = %s
                      AND m.is_active = true
                      AND c.is_active = true
                    {organization_filter}
                    ORDER BY m.created_at
                """.format(organization_filter=organization_filter), params)
                memberships = cursor.fetchall()

                if not memberships:
                    return None
                if len(memberships) > 1 and not organization_slug:
                    raise ValueError(
                        "organization_slug is required for accounts with multiple memberships"
                    )

                user = self.get_principal(user_id, memberships[0][0])
                if not user:
                    return None

                cursor.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = %s",
                    (user_id,)
                )
                self.connection.commit()
                user["last_login"] = datetime.now(timezone.utc)

                logger.info("User authenticated successfully")
                return user
                
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise
    
    def get_principal(self, user_id: int, membership_id: UUID | str) -> Optional[dict]:
        """Load the current user and authoritative active membership."""
        self._ensure_connection()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        u.id, u.public_id, u.email, u.full_name, u.is_active,
                        u.last_login, u.created_at, u.updated_at,
                        m.id, m.company_id, m.role,
                        c.public_id, c.slug
                    FROM users AS u
                    JOIN memberships AS m ON m.user_id = u.id
                    JOIN companies AS c ON c.id = m.company_id
                    WHERE u.id = %s
                      AND m.id = %s
                      AND u.is_active = true
                      AND m.is_active = true
                      AND c.is_active = true
                """, (user_id, str(membership_id)))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "public_id": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "is_active": row[4],
                    "last_login": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "membership_id": row[8],
                    "company_id": row[9],
                    "role": row[10],
                    "company_public_id": row[11],
                    "organization_slug": row[12],
                }
                
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise

    def get_user_by_id(
        self,
        user_id: int,
        membership_id: UUID | str,
    ) -> Optional[dict]:
        """Compatibility wrapper for principal loading."""
        return self.get_principal(user_id, membership_id)

    @staticmethod
    def _hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def create_refresh_session(self, user_id: int, membership_id: UUID | str) -> str:
        """Create an opaque, server-revocable refresh session."""
        self._ensure_connection()
        raw_token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO refresh_sessions (
                        user_id, membership_id, token_hash, expires_at
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    user_id,
                    str(membership_id),
                    self._hash_secret(raw_token),
                    expires_at,
                ))
            self.connection.commit()
            return raw_token
        except Exception:
            self.connection.rollback()
            raise

    def rotate_refresh_session(self, refresh_token: str) -> Tuple[dict, str]:
        """Consume one refresh token and atomically issue its replacement."""
        self._ensure_connection()
        replacement_token = secrets.token_urlsafe(48)
        replacement_id = uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, membership_id
                    FROM refresh_sessions
                    WHERE token_hash = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    FOR UPDATE
                """, (self._hash_secret(refresh_token),))
                row = cursor.fetchone()
                if not row:
                    raise ValueError("Invalid or expired refresh token")

                user_id, membership_id = row
                principal = self.get_principal(user_id, membership_id)
                if not principal:
                    raise ValueError("Membership is no longer active")

                cursor.execute("""
                    INSERT INTO refresh_sessions (
                        id, user_id, membership_id, token_hash, expires_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    str(replacement_id),
                    user_id,
                    str(membership_id),
                    self._hash_secret(replacement_token),
                    expires_at,
                ))
                cursor.execute("""
                    UPDATE refresh_sessions
                    SET revoked_at = NOW(),
                        last_used_at = NOW(),
                        replaced_by = %s
                    WHERE token_hash = %s
                """, (
                    str(replacement_id),
                    self._hash_secret(refresh_token),
                ))
            self.connection.commit()
            return principal, replacement_token
        except Exception:
            self.connection.rollback()
            raise

    def revoke_refresh_session(
        self,
        refresh_token: str,
        user_id: int,
        membership_id: UUID | str,
    ) -> None:
        """Idempotently revoke a refresh session."""
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE refresh_sessions
                    SET revoked_at = COALESCE(revoked_at, NOW())
                    WHERE token_hash = %s
                      AND user_id = %s
                      AND membership_id = %s
                """, (
                    self._hash_secret(refresh_token),
                    user_id,
                    str(membership_id),
                ))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
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
                normalized_email = email.strip().lower()

                # Existing identities may join another organization, but an
                # existing membership must not be duplicated.
                cursor.execute("""
                    SELECT 1
                    FROM users AS u
                    JOIN memberships AS m ON m.user_id = u.id
                    WHERE m.company_id = %s
                      AND u.email = %s
                      AND m.is_active = true
                """, (company_id, normalized_email))
                if cursor.fetchone():
                    raise ValueError(f"User with email '{email}' already exists in this company")

                token = secrets.token_urlsafe(32)
                token_hash = self._hash_secret(token)
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                
                cursor.execute("""
                    INSERT INTO invitations (
                        company_id, email, role, token, token_hash,
                        invited_by, expires_at, accepted_at
                    )
                    VALUES (%s, %s, %s, NULL, %s, %s, %s, NULL)
                    ON CONFLICT (company_id, email) DO UPDATE
                    SET role = EXCLUDED.role,
                        token = NULL,
                        token_hash = EXCLUDED.token_hash,
                        invited_by = EXCLUDED.invited_by,
                        expires_at = EXCLUDED.expires_at,
                        accepted_at = NULL,
                        created_at = NOW()
                    RETURNING id, company_id, email, role, invited_by,
                              expires_at, accepted_at, created_at
                """, (
                    company_id,
                    normalized_email,
                    role,
                    token_hash,
                    invited_by,
                    expires_at,
                ))
                
                row = cursor.fetchone()
                invitation = {
                    "id": row[0],
                    "company_id": row[1],
                    "email": row[2],
                    "role": row[3],
                    "invited_by": row[4],
                    "expires_at": row[5],
                    "accepted_at": row[6],
                    "created_at": row[7],
                    "invitation_token": token,
                }
                
                self.connection.commit()
                logger.info("Created organization invitation")
                
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
                    WHERE token_hash = %s
                    FOR UPDATE
                """, (self._hash_secret(token),))
                
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
                if invitation["expires_at"] < datetime.now(timezone.utc):
                    raise ValueError("Invitation has expired")

                cursor.execute("""
                    SELECT id, password_hash, is_active
                    FROM users
                    WHERE email = %s
                """, (invitation["email"],))
                existing_user = cursor.fetchone()

                if existing_user:
                    user_id, existing_hash, is_active = existing_user
                    if not is_active or not self.verify_password(password, existing_hash):
                        raise ValueError("Invalid account credentials")
                else:
                    password_hash = self.hash_password(password)
                    legacy_role = {
                        "owner": "company_admin",
                        "admin": "hr_manager",
                        "member": "employee",
                    }[invitation["role"]]
                    cursor.execute("""
                        INSERT INTO users (
                            company_id, email, password_hash, full_name,
                            role, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, true)
                        RETURNING id
                    """, (
                        invitation["company_id"],
                        invitation["email"],
                        password_hash,
                        full_name,
                        legacy_role,
                    ))
                    user_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO memberships (company_id, user_id, role, is_active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (company_id, user_id) DO UPDATE
                    SET role = EXCLUDED.role,
                        is_active = true,
                        updated_at = NOW()
                    RETURNING id
                """, (
                    invitation["company_id"],
                    user_id,
                    invitation["role"],
                ))
                membership_id = cursor.fetchone()[0]
                
                # Mark invitation as accepted
                cursor.execute("""
                    UPDATE invitations
                    SET accepted_at = NOW(), token_hash = NULL
                    WHERE id = %s
                """, (invitation["id"],))

                user = self.get_principal(user_id, membership_id)
                company = self.get_company_by_id(invitation["company_id"])
                self.connection.commit()
                logger.info("Organization invitation accepted")
                
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
