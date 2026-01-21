"""
User schemas for API validation.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.schemas.role import RoleResponse


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str
    role_id: Optional[int] = 2  # Default to 'user' role


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None


class UserResponse(UserBase):
    """Schema for user response (without password)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_active: bool
    role: RoleResponse
    created_at: datetime
    updated_at: datetime


class UserInDB(UserBase):
    """Schema for user in database (with hashed password)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    hashed_password: str
    is_active: bool
    role_id: int
