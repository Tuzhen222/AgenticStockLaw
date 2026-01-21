"""
Authentication router with JWT login and registration.
Uses AuthService for business logic.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Annotated

from app.db.session import get_db
from app.db.schemas import Token, UserCreate, UserResponse, RefreshTokenRequest
from app.services import auth_service
from app.core.deps import CurrentUser
from app.core.security import verify_token
from app.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    Login with email and password.
    Returns access and refresh tokens.
    """
    logger.info(f"Login attempt for email: {form_data.username}")
    
    result = auth_service.login(
        db, 
        email=form_data.username,  # OAuth2 form uses 'username' field
        password=form_data.password
    )
    
    logger.info(f"Login successful for email: {form_data.username}")
    return result


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    db: Annotated[Session, Depends(get_db)],
    user_in: UserCreate,
) -> UserResponse:
    """
    Register a new user.
    Default role is 'user' (role_id=2).
    """
    logger.info(f"Registration attempt for email: {user_in.email}, username: {user_in.username}")
    
    result = auth_service.register(db, user_in=user_in)
    
    logger.info(f"Registration successful for user: {user_in.username} (ID: {result.id})")
    return result


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user info.
    """
    logger.debug(f"User info requested for: {current_user.username} (ID: {current_user.id})")
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(
    db: Annotated[Session, Depends(get_db)],
    token_request: RefreshTokenRequest,
) -> Token:
    """
    Refresh access token using refresh token.
    Does not require valid access token - uses refresh_token from request body.
    """
    # Verify the refresh token
    user_id = verify_token(token_request.refresh_token, token_type="refresh")
    
    if user_id is None:
        logger.warning("Invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists and is active
    user = auth_service.get_user_by_id(db, user_id=int(user_id))
    if user is None or not user.is_active:
        logger.warning(f"Refresh token for invalid/inactive user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Token refresh for user: {user.username} (ID: {user.id})")
    return auth_service.refresh_tokens(user_id=user.id)
