from pydantic import BaseModel, Field
from typing import List

class ConversionRequest(BaseModel):
    target_format: str = Field(..., regex="^(xlsx|csv|pdf|mp3|png|jpg)$")

SUPPORTED_FORMATS = ["csv", "xlsx", "pdf", "jpg", "png", "txt", "wav", "mp3"]
