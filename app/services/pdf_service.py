from pypdf import PdfReader, PdfWriter
from io import BytesIO
import img2pdf
try:
    from docx2pdf import convert as docx2pdf
except Exception:
    docx2pdf = None
from typing import List
try:
    import fitz  # PyMuPDF for better conversion
except Exception:
    fitz = None
import os

class PDFService:
    @staticmethod
    def merge_pdfs(pdf_files: List[bytes]) -> bytes:
        """Merge multiple PDF files into one."""
        merger = PdfWriter()
        
        for pdf_content in pdf_files:
            reader = PdfReader(BytesIO(pdf_content))
            for page in reader.pages:
                merger.add_page(page)
        
        output = BytesIO()
        merger.write(output)
        output.seek(0)
        return output.read()
    
    @staticmethod
    def file_to_pdf(file_content: bytes, mime_type: str) -> bytes:
        """Convert various formats to PDF."""
        if "image/" in mime_type:
            return img2pdf.convert(file_content)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if docx2pdf is None:
                raise ValueError("DOCX conversion is unavailable: install docx2pdf")
            # Save temp file for docx conversion
            with open("temp.docx", "wb") as f:
                f.write(file_content)
            docx2pdf.convert("temp.docx", "temp.pdf")
            with open("temp.pdf", "rb") as f:
                result = f.read()
            os.remove("temp.docx")
            os.remove("temp.pdf")
            return result
        elif mime_type == "text/plain":
            if fitz is None:
                raise ValueError("Text-to-PDF conversion is unavailable: install PyMuPDF")
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Text content conversion not fully implemented")
            output = BytesIO()
            doc.save(output)
            doc.close()
            return output.getvalue()
        else:
            supported = "image/*, application/vnd.openxmlformats-officedocument.wordprocessingml.document (docx), text/plain"
            raise ValueError(f"Unsupported format: {mime_type}. Supported: {supported}")

pdf_service = PDFService()
