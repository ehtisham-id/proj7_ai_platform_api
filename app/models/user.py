from sqlalchemy import String, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import enum

class Role(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

ROLE_ENUM = Enum(
    Role,
    name="role",
    native_enum=True,
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(ROLE_ENUM, default=Role.USER)
