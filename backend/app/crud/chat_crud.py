"""
CRUD operations for chat history.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.chat_models import ChatSession, ChatMessage


# ============ Chat Sessions ============

def create_session(db: Session, user_id: int, title: str = "New Chat") -> ChatSession:
    """Create a new chat session for a user."""
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_sessions(db: Session, user_id: int, limit: int = 50) -> List[ChatSession]:
    """Get all chat sessions for a user, ordered by most recent."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .limit(limit)
        .all()
    )


def get_session(db: Session, session_id: int, user_id: int) -> Optional[ChatSession]:
    """Get a specific session by ID (with user ownership check)."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )


def update_session_title(db: Session, session_id: int, user_id: int, title: str) -> Optional[ChatSession]:
    """Update session title."""
    session = get_session(db, session_id, user_id)
    if session:
        session.title = title
        db.commit()
        db.refresh(session)
    return session


def delete_session(db: Session, session_id: int, user_id: int) -> bool:
    """Delete a session and all its messages."""
    session = get_session(db, session_id, user_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


# ============ Chat Messages ============

def create_message(
    db: Session, 
    session_id: int, 
    role: str, 
    content: str, 
    extra_data: Optional[dict] = None
) -> ChatMessage:
    """Create a new message in a session."""
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        extra_data=extra_data
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Update session's updated_at
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        from sqlalchemy.sql import func
        session.updated_at = func.now()
        db.commit()
    
    return message


def get_messages(db: Session, session_id: int, limit: int = 100) -> List[ChatMessage]:
    """Get all messages in a session, ordered by creation time."""
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )


def create_message_pair(
    db: Session,
    session_id: int,
    user_content: str,
    assistant_content: str,
    extra_data: Optional[dict] = None
) -> tuple:
    """Create both user and assistant messages at once."""
    user_msg = create_message(db, session_id, "user", user_content)
    assistant_msg = create_message(db, session_id, "assistant", assistant_content, extra_data)
    return user_msg, assistant_msg
