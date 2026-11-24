from app.core.config import settings
from minio import Minio

def get_minio_client():
    """
    Get a Minio client instance.
    Initialize S3 client (minio SDK against RustFS — plain S3, vendor-neutral)
    
    Returns:
        Minio: A Minio client instance.
    """
    return Minio(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=False,
    )