"""
Base model with common fields and utilities.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.db.session import Base


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""
    
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )


class UUIDMixin:
    """Mixin that adds UUID primary key."""
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID primary key and timestamps."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

