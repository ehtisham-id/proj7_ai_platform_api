from fastapi import APIRouter, Depends, UploadFile, File as FileParam, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.services.minio_service import minio_service
from app.services.ar_menu_service import ar_menu_service
from app.services.pdf_service import pdf_service
import json

router = APIRouter(prefix="/ar/menu", tags=["AR Menu"])

@router.post("/create", response_model=dict)
async def create_ar_menu(
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if file.content_type not in ["text/csv", "application/json"]:
        raise HTTPException(status_code=400, detail="Only CSV/JSON supported")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Parse menu data
        menu_items = ar_menu_service.parse_menu_data(content, file.content_type)
        
        # Generate AR menu
        ar_menu = ar_menu_service.generate_ar_menu(menu_items)
        
        # Save AR menu JSON
        menu_json = json.dumps(ar_menu, indent=2).encode('utf-8')
        menu_filename = f"ar-menu-{ar_menu['id']}.json"
        menu_object_name = minio_service.upload_file(
            filename=menu_filename,
            file_content=menu_json,
            metadata={'type': 'ar_menu_json', 'user_id': str(current_user.id)}
        )
        
        # Save preview image
        preview_image = ar_menu_service.generate_preview(menu_items)
        preview_filename = f"ar-menu-preview-{ar_menu['id']}.png"
        preview_object_name = minio_service.upload_file(
            filename=preview_filename,
            file_content=preview_image,
            metadata={'type': 'ar_menu_preview'}
        )
        preview_url = minio_service.get_presigned_url(preview_object_name)
        
        # Save to database
        db_file = FileModel(
            filename=menu_filename,
            user_id=current_user.id,
            object_name=menu_object_name,
            mime_type="application/json",
            size_bytes=len(menu_json)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return {
            "ar_menu_id": db_file.id,
            "preview_url": preview_url,
            "item_count": len(menu_items),
            "qr_count": len(ar_menu['qr_codes']),
            "menu_url": minio_service.get_presigned_url(menu_object_name)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AR menu generation failed: {str(e)}")
