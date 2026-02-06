from fastapi import APIRouter, Depends, UploadFile, File as FileParam, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.services.minio_service import minio_service
from app.services.analysis_service import analysis_service
import json
from io import BytesIO
import pandas as pd
import uuid

router = APIRouter(prefix="/analysis", tags=["Data Analysis"])

@router.post("/upload", response_model=dict)
async def analyze_dataset(
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file type
    if not file.content_type or file.content_type not in ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        raise HTTPException(status_code=400, detail="Only CSV/Excel files supported")
    
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Analyze dataset
        file_type = 'text/csv' if file.content_type == 'text/csv' else 'excel'
        analysis_result = analysis_service.analyze_dataset(content, file_type)
        
        # Save analysis JSON
        analysis_json = json.dumps(analysis_result, indent=2).encode('utf-8')
        filename = f"analysis_{uuid.uuid4().hex[:8]}.json"
        object_name = minio_service.upload_file(
            filename=filename,
            file_content=analysis_json,
            metadata={
                'type': 'analysis_report',
                'rows': analysis_result['summary']['rows'],
                'user_id': str(current_user.id)
            }
        )
        
        # Generate and save charts
        if file_type == 'text/csv':  # Pandas can read from bytes for charts
            df = pd.read_csv(BytesIO(content))
            charts_urls = analysis_service.generate_charts(df, "")
        else:
            charts_urls = []
        
        # Save dataset to DB
        db_file = FileModel(
            filename=filename,
            user_id=current_user.id,
            object_name=object_name,
            mime_type="application/json",
            size_bytes=len(analysis_json)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        return {
            "analysis_id": db_file.id,
            "summary": analysis_result["summary"],
            "charts_url": charts_urls,
            "insights": analysis_result["summary"].get("insights", []),
            "columns": analysis_result["columns"],
            "sample_data": analysis_result["sample_data"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
