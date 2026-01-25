from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import Role

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Role = Role.USER

class UserOut(UserBase):
    id: int
    role: Role
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
