import uuid
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from app.core.config import settings
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".csv"}


@router.post("/upload", status_code=202)
async def upload_document(request: Request, file: UploadFile):
    # 1. Validate - reject non-whitelisted extensions with 415
    if not file.filename or not Path(file.filename).suffix.lower() in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="File type not allowed")

    # 2. Stream to Bronze - upload to S3
    object_name = f"{uuid.uuid4()}-{Path(file.filename).name}"
    await asyncio.to_thread(
        request.app.state.s3_client.put_object,
        bucket_name=settings.s3_bucket_raw,
        object_name=object_name,
        content_type=file.content_type,
        data=file.file,
        length=-1,
        part_size=10*1024*1024,  # 10MB parts
    )

    # 3. Send task to Celery
    await asyncio.to_thread(
        celery_app.send_task,
        "extract_document",
        kwargs={
            "object_name": object_name,
            "bucket_name": settings.s3_bucket_raw,
            "file_name": Path(file.filename).name
        }
    )

    return {
        "object_name": object_name,
        "bucket": settings.s3_bucket_raw,
        "queued": True
    }