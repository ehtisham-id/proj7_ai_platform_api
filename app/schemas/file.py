from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileBase(BaseModel):
    filename: str
    mime_type: Optional[str] = None

class FileCreate(FileBase):
    pass

class FileOut(FileBase):
    id: int
    object_name: str
    version: int
    size_bytes: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FileVersionOut(BaseModel):
    version: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class FileRename(BaseModel):
    new_name: str
