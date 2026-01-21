"""
Security utilities for JWT authentication and password hashing.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bcrypt has a maximum password length of 72 bytes
MAX_PASSWORD_LENGTH = 72


def _truncate_password(password: str) -> bytes:
    """
    Truncate password to maximum bcrypt length.
    
    Bcrypt has a 72-byte limit. This function encodes the password to UTF-8
    and truncates it to 72 bytes if necessary.
    
    Args:
        password: The plain text password
        
    Returns:
        Password as bytes, truncated to 72 bytes if necessary
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > MAX_PASSWORD_LENGTH:
        password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
    return password_bytes


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    exp: Optional[datetime] = None
    type: Optional[str] = None


class TokenData(BaseModel):
    """Token data returned after creation."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    # Truncate password to 72 bytes to avoid bcrypt limit error
    truncated_password = _truncate_password(plain_password)
    return pwd_context.verify(truncated_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The hashed password string
    """
    # Truncate password to 72 bytes to avoid bcrypt limit error
    truncated_password = _truncate_password(password)
    return pwd_context.hash(truncated_password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID or email)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user ID or email)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_tokens(subject: Union[str, Any]) -> TokenData:
    """
    Create both access and refresh tokens.
    
    Args:
        subject: The subject of the tokens
        
    Returns:
        TokenData with access_token, refresh_token, and token_type
    """
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)
    
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string to decode
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload(**payload)
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify a token and return the subject if valid.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        The subject (user identifier) if valid, None otherwise
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    if payload.type != token_type:
        return None
    
    if payload.exp and payload.exp < datetime.now(timezone.utc):
        return None
    
    return payload.sub


# FastAPI dependencies
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.db.models import User
    from app.db.session import SessionLocal
    from sqlalchemy.orm import Session
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(token, token_type="access")
    
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    try:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user is None:
                raise credentials_exception
            return user
        finally:
            db.close()
    except Exception:
        raise credentials_exception


async def get_current_active_user(current_user = Depends(get_current_user)):
    """
    Get current active user (not disabled).
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
