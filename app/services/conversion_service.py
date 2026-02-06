import pandas as pd
from io import BytesIO
import img2pdf
import os
from typing import Dict, Any

try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None

class ConversionService:
    # Image formats that can be converted to PDF
    IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
    
    SUPPORTED_CONVERSIONS = {
        'csv_to_excel': lambda data: ConversionService.csv_to_excel(data),
        'csv_to_xlsx': lambda data: ConversionService.csv_to_excel(data),
        'excel_to_csv': lambda data: ConversionService.excel_to_csv(data),
        'xlsx_to_csv': lambda data: ConversionService.excel_to_csv(data),
        'xls_to_csv': lambda data: ConversionService.excel_to_csv(data),
        'image_to_pdf': lambda data: img2pdf.convert(data),
        'txt_to_pdf': lambda data: ConversionService.txt_to_pdf(data),
        'text_to_pdf': lambda data: ConversionService.txt_to_pdf(data),
        'plain_to_pdf': lambda data: ConversionService.txt_to_pdf(data),
    }
    
    @staticmethod
    def csv_to_excel(csv_bytes: bytes) -> bytes:
        df = pd.read_csv(BytesIO(csv_bytes))
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        return output.getvalue()
    
    @staticmethod
    def excel_to_csv(excel_bytes: bytes) -> bytes:
        df = pd.read_excel(BytesIO(excel_bytes))
        output = BytesIO()
        df.to_csv(output, index=False)
        return output.getvalue()
    
    @staticmethod
    def txt_to_pdf(txt_bytes: bytes) -> bytes:
        text = txt_bytes.decode('utf-8')
        # Simple text to PDF (using reportlab or similar)
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
        except Exception as exc:
            raise ValueError("Text-to-PDF conversion is unavailable: install reportlab") from exc
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50
        for line in text.split('\n'):
            if y < 50:
                p.showPage()
                y = height - 50
            p.drawString(50, y, line[:80])
            y -= 14
        p.save()
        buffer.seek(0)
        return buffer.read()
    
    @staticmethod
    def audio_to_mp3(audio_bytes: bytes, input_format: str) -> bytes:
        if AudioSegment is None:
            raise ValueError("Audio conversion is unavailable: install pydub and ffmpeg")
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format=input_format)
        output = BytesIO()
        audio.export(output, format="mp3", bitrate="192k")
        return output.getvalue()
    
    @staticmethod
    def convert_file(file_content: bytes, source_format: str, target_format: str) -> bytes:
        source_lower = source_format.lower()
        target_lower = target_format.lower()
        
        # Handle image to PDF conversion for various image formats
        if source_lower in ConversionService.IMAGE_FORMATS and target_lower == 'pdf':
            return img2pdf.convert(file_content)
        
        conversion_key = f"{source_lower}_to_{target_lower}"
        if conversion_key in ConversionService.SUPPORTED_CONVERSIONS:
            return ConversionService.SUPPORTED_CONVERSIONS[conversion_key](file_content)
        if target_lower == "mp3":
            return ConversionService.audio_to_mp3(file_content, source_lower)
        raise ValueError(f"Unsupported conversion: {source_format} → {target_format}")

conversion_service = ConversionService()
