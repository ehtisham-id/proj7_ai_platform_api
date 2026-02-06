from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any

class PhotoEdit(BaseModel):
    filter: Optional[str] = Field(None, pattern="^(grayscale|blur|sharpen|edge|vintage|brighten|sepia)$")
    rotate: Optional[int] = Field(None, ge=-360, le=360)
    resize: Optional[Dict[str, int]] = None
    
    @field_validator('resize')
    def validate_resize(cls, v):
        if v:
            if not all(k in v for k in ['width', 'height']):
                raise ValueError('resize must contain width and height')
            if v['width'] < 1 or v['height'] < 1:
                raise ValueError('width and height must be positive')
        return v
