from pydantic import BaseModel
from typing import List, Optional

class MenuItem(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    category: Optional[str] = "main"

class ARMenuCreate(BaseModel):
    pass  # File upload handled separately

class ARMenuResponse(BaseModel):
    ar_menu_id: int
    preview_url: str
    item_count: int
    qr_count: int
