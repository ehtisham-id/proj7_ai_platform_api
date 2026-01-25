import pandas as pd
import json
import uuid
from typing import Dict, List, Any
from app.services.minio_service import minio_service
from app.services.qr_service import qr_service
import base64
from io import BytesIO
import qrcode
from PIL import Image, ImageDraw, ImageFont

class ARMenuService:
    @staticmethod
    def parse_menu_data(file_content: bytes, file_type: str) -> List[Dict]:
        """Parse CSV/JSON menu data into standardized format."""
        if file_type == "text/csv":
            df = pd.read_csv(BytesIO(file_content))
        elif file_type == "application/json":
            df = pd.read_json(BytesIO(file_content))
        else:
            raise ValueError("Unsupported file type")
        
        # Standardize columns: name, price, description, image_url, category
        required_cols = ['name', 'price']
        if not all(col in df.columns for col in required_cols):
            raise ValueError("Missing required columns: name, price")
        
        menu_items = []
        for _, row in df.iterrows():
            item = {
                'id': str(uuid.uuid4()),
                'name': str(row.get('name', '')),
                'price': float(row.get('price', 0)),
                'description': str(row.get('description', '')),
                'category': str(row.get('category', 'main')),
                'image_url': str(row.get('image_url', '')),
                'ar_model': f"3d/{row.get('name', 'item')}.glb"  # Placeholder
            }
            menu_items.append(item)
        
        return menu_items
    
    @staticmethod
    def generate_ar_menu(menu_items: List[Dict]) -> Dict[str, Any]:
        """Generate AR menu JSON with QR codes and 3D markers."""
        ar_menu = {
            'id': str(uuid.uuid4()),
            'items': menu_items,
            'markers': [],
            'qr_codes': []
        }
        
        # Generate QR codes for each item
        for item in menu_items:
            qr_text = f"https://ar.ai-platform.com/menu/{ar_menu['id']}/{item['id']}"
            qr_data = {
                'text': qr_text,
                'size': 256,
                'color': '#0066CC',
                'background': '#FFFFFF'
            }
            
            # Generate QR image (bytes)
            qr_image = qr_service.generate_qr(**qr_data)
            
            # Save QR to MinIO
            qr_filename = f"ar-menu-qr-{item['id'][:8]}.png"
            qr_object_name = minio_service.upload_file(
                filename=qr_filename,
                file_content=qr_image,
                metadata={'type': 'ar_menu_qr', 'menu_id': ar_menu['id']}
            )
            qr_url = minio_service.get_presigned_url(qr_object_name)
            
            item['qr_url'] = qr_url
            ar_menu['qr_codes'].append({
                'item_id': item['id'],
                'qr_url': qr_url,
                'scan_url': qr_text
            })
        
        return ar_menu
    
    @staticmethod
    def generate_preview(menu_items: List[Dict]) -> bytes:
        """Generate visual menu preview."""
        # Create a simple grid preview
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        y_offset = 50
        for i, item in enumerate(menu_items[:6]):  # First 6 items
            draw.rectangle([50, y_offset, 750, y_offset + 80], outline='black', width=2)
            draw.text((60, y_offset + 10), f"🍽️ {item['name']}", fill='black', font=font)
            draw.text((60, y_offset + 40), f"${item['price']:.2f}", fill='#0066CC', font=font)
            y_offset += 90
        
        draw.text((50, 10), "AR Menu Preview", fill='#0066CC', font=font)
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

ar_menu_service = ARMenuService()
