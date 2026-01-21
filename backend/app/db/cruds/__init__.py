"""
CRUD operations module.
Import your CRUD classes here.
"""
from app.db.cruds.role import crud_role
from app.db.cruds.user import crud_user

__all__ = ["crud_role", "crud_user"]
