import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
from typing import Dict, Any, Optional
import uuid

class PhotoService:
    FILTERS = {
        'grayscale': lambda img: cv2.cvtColor(img, cv2.COLOR_RGB2GRAY),
        'blur': lambda img: cv2.GaussianBlur(img, (15, 15), 0),
        'sharpen': lambda img: cv2.filter2D(img, -1, np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])),
        'edge': lambda img: cv2.Canny(img, 100, 200),
        'vintage': lambda img: PhotoService._vintage_filter(img),
        'brighten': lambda img: np.clip(img * 1.3, 0, 255).astype(np.uint8)
    }
    
    @staticmethod
    def _vintage_filter(img: np.ndarray) -> np.ndarray:
        """Sepia/vintage effect."""
        sepia_filter = np.array([[0.393, 0.769, 0.189],
                               [0.349, 0.686, 0.168],
                               [0.272, 0.534, 0.131]])
        sepia_img = cv2.transform(img, sepia_filter)
        sepia_img[np.where(sepia_img > 255)] = 255
        return sepia_img.astype(np.uint8)
    
    @staticmethod
    def apply_filter(img: np.ndarray, filter_name: str) -> np.ndarray:
        """Apply image filter."""
        if filter_name in PhotoService.FILTERS:
            return PhotoService.FILTERS[filter_name](img)
        return img
    
    @staticmethod
    def resize_image(img: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize with aspect ratio preservation."""
        h, w = img.shape[:2]
        if width and height:
            return cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
        return img
    
    @staticmethod
    def rotate_image(img: np.ndarray, angle: int) -> np.ndarray:
        """Rotate image by angle."""
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(img, matrix, (w, h))
    
    @staticmethod
    def process_photo(image_bytes: bytes, operations: Dict[str, Any]) -> bytes:
        """Process photo with multiple operations."""
        # Load image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image")
        
        # Apply operations
        if 'filter' in operations:
            img = PhotoService.apply_filter(img, operations['filter'])
        
        if 'rotate' in operations:
            img = PhotoService.rotate_image(img, operations['rotate'])
        
        if 'resize' in operations:
            size = operations['resize']
            img = PhotoService.resize_image(img, size.get('width'), size.get('height'))
        
        # Encode result
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buffer.tobytes()

photo_service = PhotoService()
