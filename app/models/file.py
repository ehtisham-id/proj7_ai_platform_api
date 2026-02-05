from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from typing import List

class File(Base):
    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Foreign key
    bucket: Mapped[str] = mapped_column(String, default="ai-platform")
    object_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    mime_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    versions: Mapped[List["FileVersion"]] = relationship("FileVersion", back_populates="file")
