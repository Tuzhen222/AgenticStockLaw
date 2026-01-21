"""
Role schemas for API validation.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    """Base role schema."""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    pass


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    """Schema for role response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
