"""
User CRUD operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class CRUDUser:
    """CRUD operations for User model."""

    def get(self, db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get multiple users."""
        return db.query(User).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            full_name=obj_in.full_name,
            hashed_password=get_password_hash(obj_in.password),
            role_id=obj_in.role_id or 2,  # Default to 'user' role
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        """Update a user."""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Hash password if being updated
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, user_id: int) -> Optional[User]:
        """Delete a user."""
        obj = db.query(User).filter(User.id == user_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active


# Singleton instance
crud_user = CRUDUser()
