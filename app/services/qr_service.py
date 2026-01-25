import qrcode
from PIL import Image
from io import BytesIO
from typing import Optional, Dict, Any
import uuid

class QRService:
    @staticmethod
    def generate_qr(
        text: str,
        size: int = 300,
        border: int = 4,
        color: str = "#000000",
        background: str = "#FFFFFF",
        logo_path: Optional[str] = None,
        logo_scale: float = 0.25
    ) -> bytes:
        """Generate QR code with customization options."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(
            fill_color=color,
            back_color=background,
            image_factory=None  # Use default PIL
        ).resize((size, size), Image.Resampling.LANCZOS)
        
        # Add logo if provided
        if logo_path:
            logo = Image.open(logo_path)
            logo_size = int(size * logo_scale)
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            pos = ((size - logo_size) // 2, (size - logo_size) // 2)
            img.paste(logo, pos, logo)
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output.read()

qr_service = QRService()
