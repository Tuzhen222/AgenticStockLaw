"""
Role CRUD operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.models import Role
from app.db.schemas.role import RoleCreate, RoleUpdate


class CRUDRole:
    """CRUD operations for Role model."""

    def get(self, db: Session, role_id: int) -> Optional[Role]:
        """Get role by ID."""
        return db.query(Role).filter(Role.id == role_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Role]:
        """Get role by name."""
        return db.query(Role).filter(Role.name == name).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
        """Get multiple roles."""
        return db.query(Role).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: RoleCreate) -> Role:
        """Create a new role."""
        db_obj = Role(
            name=obj_in.name,
            description=obj_in.description,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Role, obj_in: RoleUpdate) -> Role:
        """Update a role."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, role_id: int) -> Optional[Role]:
        """Delete a role."""
        obj = db.query(Role).filter(Role.id == role_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# Singleton instance
crud_role = CRUDRole()
