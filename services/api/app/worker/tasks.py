import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

from docling.document_converter import DocumentConverter
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.worker.celery_app import celery_app
from app.core.storage import get_minio_client
from app.core.config import settings

logger = logging.getLogger(__name__)

@celery_app.task(name="extract_document")
def extract_document(object_name: str, bucket_name: str, file_name: str):
    tmp_file_path = None
    response = None
    # Initialize MinIO client
    minio_client = get_minio_client()

    try:
        # 1. Download the file from MinIO
        response = minio_client.get_object(bucket_name, object_name)

        # 2. Write downloaded content to a temp file
        with NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
            tmp_file.write(response.read())
            tmp_file_path = tmp_file.name
        
        # 3. Convert the document to markdown
        converter = DocumentConverter()
        result = converter.convert(tmp_file_path)
        markdown = result.document.export_to_markdown()

        # 4. Log extraction result
        logger.info(
            "Document extracted: %s, characters: %d",
            object_name,
            len(markdown)
        )

        return {
            "object_name": object_name,
            "markdown_chars": len(markdown)
        }
    
    except Exception as e:
        logger.error("Failed to extract document: %s", e)
        raise
    finally:
        # Close minio response
        if response is not None:
            response.close()
            response.release_conn()
        
        # Clean up temp file
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            logger.info("Temp file cleaned up: %s", tmp_file_path)