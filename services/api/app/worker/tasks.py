import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import io

from celery.signals import worker_process_init

from docling.document_converter import DocumentConverter
from minio import Minio
from minio.error import S3Error

from app.worker.celery_app import celery_app
from app.core.storage import get_minio_client
from app.core.config import settings

logger = logging.getLogger(__name__)

_converter = None
_s3_client: Minio | None = None


def _get_s3_client() -> Minio:
    global _s3_client
    if _s3_client is None:
        _s3_client = get_minio_client()
    return _s3_client

@worker_process_init.connect
def ensure_silver_bucket(**kwargs):
    global _converter
    if _converter is None:
        _converter = DocumentConverter()

    client = _get_s3_client()
    bucket = settings.s3_bucket_processed

    try:
        client.make_bucket(bucket)
        logger.info("Created bucket: %s", bucket)
    except S3Error as e:
        if e.code == "BucketAlreadyOwnedByYou":
            logger.info("Bucket already exists: %s", bucket)
        else:
            logger.error("Failed to create bucket: %s", e)
            raise
    

@celery_app.task(
    name="extract_document",
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_jitter=True,
    max_retries=3
)
def extract_document(object_name: str, bucket_name: str, file_name: str):
    tmp_file_path = None
    response = None

    try:
        # 1. Download the file from S3
        response = _get_s3_client().get_object(bucket_name, object_name)

        # 2. Write downloaded content to a temp file
        with NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
            for chunk in response.stream(32 * 1024):  # 32KB chunks
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        # 3. Convert the document to markdown
        result = _converter.convert(tmp_file_path) # type: ignore
        markdown = result.document.export_to_markdown()
        markdown_bytes = markdown.encode("utf-8")

        # 4. Upload markdown to S3 - Silver layer
        _get_s3_client().put_object(  # type: ignore
            bucket_name=settings.s3_bucket_processed,
            object_name=f"{object_name}.md",
            data=io.BytesIO(markdown_bytes),
            length=len(markdown_bytes),
            content_type="text/markdown",
            metadata={
                "source-object": object_name,
                "source-filename": file_name,
            }
        )

        # 5. Log extraction result
        logger.info(
            "Document extracted: %s, characters: %d",
            object_name,
            len(markdown)
        )

        return {
            "object_name": object_name,
            "markdown_object": f"{object_name}.md",
            "markdown_chars": len(markdown)
        }
    
    except Exception as e:
        logger.exception("Failed to extract document: %s", e)
        raise
    finally:
        # Close client response
        if response is not None:
            response.close()
            response.release_conn()
        
        # Clean up temp file
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            logger.info("Temp file cleaned up: %s", tmp_file_path)