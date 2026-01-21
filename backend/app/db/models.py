"""
SQLAlchemy models for PostgreSQL database.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class BaseModel(Base):
    """
    Abstract base model with common fields.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Role(BaseModel):
    """
    Role model for user authorization.
    Default roles: 'admin', 'user'
    """
    __tablename__ = "roles"

    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    # Relationships
    users = relationship("User", back_populates="role")


class User(BaseModel):
    """
    User model for authentication.
    """
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    # Foreign Keys
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, default=2)

    # Relationships
    role = relationship("Role", back_populates="users")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
