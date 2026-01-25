import pandas as pd
from io import BytesIO
import img2pdf
from pydub import AudioSegment
import os
from typing import Dict, Any

class ConversionService:
    SUPPORTED_CONVERSIONS = {
        'csv_to_excel': lambda data: ConversionService.csv_to_excel(data),
        'excel_to_csv': lambda data: ConversionService.excel_to_csv(data),
        'image_to_pdf': lambda data: img2pdf.convert(data),
        'txt_to_pdf': lambda data: ConversionService.txt_to_pdf(data),
        'audio_to_mp3': lambda data: ConversionService.audio_to_mp3(data),
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
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
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
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format=input_format)
        output = BytesIO()
        audio.export(output, format="mp3", bitrate="192k")
        return output.getvalue()
    
    @staticmethod
    def convert_file(file_content: bytes, source_format: str, target_format: str) -> bytes:
        conversion_key = f"{source_format}_to_{target_format}"
        if conversion_key in ConversionService.SUPPORTED_CONVERSIONS:
            return ConversionService.SUPPORTED_CONVERSIONS[conversion_key](file_content)
        raise ValueError(f"Unsupported conversion: {source_format} → {target_format}")

conversion_service = ConversionService()
