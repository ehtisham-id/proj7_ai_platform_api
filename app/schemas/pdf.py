from pydantic import BaseModel
from typing import List

class PDFMerge(BaseModel):
    files: List[bytes]  # Handled via UploadFile

class PDFConvert(BaseModel):
    pass  # Single file upload
