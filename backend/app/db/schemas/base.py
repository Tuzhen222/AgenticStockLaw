"""
Base Pydantic schemas with common configurations.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.
    """
    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseSchema):
    """
    Base response schema with common fields.
    """
    id: int
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """
    Pagination parameters schema.
    """
    skip: int = 0
    limit: int = 100


class MessageResponse(BaseModel):
    """
    Simple message response schema.
    """
    message: str
    success: bool = True
