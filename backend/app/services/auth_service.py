"""
Authentication service layer.
Handles business logic between router and CRUD operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import User
from app.db.cruds import crud_user, crud_role
from app.db.schemas import UserCreate, Token
from app.core.security import create_tokens
from app.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class AuthService:
    """
    Authentication service for user login, registration, and token management.
    """

    def authenticate(self, db: Session, email: str, password: str) -> User:
        """
        Authenticate user by email and password.
        """
        user = crud_user.authenticate(db, email=email, password=password)
        
        if not user:
            logger.warning(f"Failed login attempt for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )
        
        logger.debug(f"User authenticated: {email} (ID: {user.id})")
        return user

    def login(self, db: Session, email: str, password: str) -> Token:
        """
        Login user and return JWT tokens.
        """
        user = self.authenticate(db, email, password)
        tokens = create_tokens(subject=str(user.id))
        
        logger.info(f"Tokens generated for user: {email} (ID: {user.id})")
        return Token(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type="bearer",
        )

    def register(self, db: Session, user_in: UserCreate) -> User:
        """
        Register a new user.
        """
        # Check if email already exists
        if crud_user.get_by_email(db, email=user_in.email):
            logger.warning(f"Registration failed - email exists: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        
        # Check if username already exists
        if crud_user.get_by_username(db, username=user_in.username):
            logger.warning(f"Registration failed - username exists: {user_in.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        
        # Ensure role exists
        role = crud_role.get(db, role_id=user_in.role_id or 2)
        if not role:
            logger.error(f"Registration failed - invalid role_id: {user_in.role_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role",
            )
        
        user = crud_user.create(db, obj_in=user_in)
        logger.info(f"New user registered: {user.username} (ID: {user.id}, email: {user.email})")
        return user

    def refresh_tokens(self, user_id: int) -> Token:
        """
        Generate new tokens for a user.
        """
        tokens = create_tokens(subject=str(user_id))
        
        logger.debug(f"Tokens refreshed for user ID: {user_id}")
        return Token(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type="bearer",
        )

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        """
        return crud_user.get(db, user_id=user_id)


# Singleton instance
auth_service = AuthService()
