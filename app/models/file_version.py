from sqlalchemy import ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class FileVersion(Base):
    __tablename__ = "file_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    object_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    file: Mapped["File"] = relationship("File", back_populates="versions")
