"""
Security utilities for password hashing and JWT token management.
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, UUID],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user_id)
        expires_delta: Optional custom expiration time
        additional_claims: Additional claims to include in the token
    
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode = {
        "sub": str(subject),
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, UUID],
    token_id: Union[str, UUID],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user_id)
        token_id: Unique identifier for the token (for revocation)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "token_id": str(token_id),
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string to decode
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def create_email_verification_token(email: str) -> str:
    """Create a token for email verification."""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "sub": email,
        "type": "email_verification",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def create_password_reset_token(email: str) -> str:
    """Create a token for password reset."""
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": email,
        "type": "password_reset",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

