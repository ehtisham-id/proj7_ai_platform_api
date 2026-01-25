from pydantic import BaseModel, Field
from typing import Optional

class QRGenerate(BaseModel):
    text: str = Field(..., max_length=500)
    size: int = Field(300, ge=100, le=1000)
    border: int = Field(4, ge=1, le=10)
    color: str = Field("#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    background: str = Field("#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
