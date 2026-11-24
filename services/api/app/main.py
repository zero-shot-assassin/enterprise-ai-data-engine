import logging
import asyncio

from contextlib import asynccontextmanager
from minio import Minio
from redis.asyncio import Redis
from qdrant_client import QdrantClient

from app.api.routes import documents

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)   

async def retry(operation, max_retries=5):
    """
    Retry an async operation with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            # Wait before retrying with exponential backoff
            await asyncio.sleep(2 ** attempt)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing services...")
    # Initialize S3 client (minio SDK against RustFS — plain S3, vendor-neutral)
    s3_client = Minio(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=False
    )
    bucket_name = settings.s3_bucket_raw
    
    # Check if bucket exists, create if not
    bucket_exists = await retry(
        lambda: asyncio.to_thread(s3_client.bucket_exists, bucket_name)
    )
    
    if not bucket_exists:
        logger.info(f"Bucket does not exist: {bucket_name}")
        await retry(
            lambda: asyncio.to_thread(s3_client.make_bucket, bucket_name)
        )
        logger.info(f"Created bucket: {bucket_name}")
    else:
        logger.info(f"Bucket already exists: {bucket_name}")
    
    # Initialize redis client
    redis_client = Redis.from_url(
        url=settings.redis_url
    )
    await retry(redis_client.ping)
    
    # Initialize qdrant client
    qdrant_client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )
    await retry(
        lambda: asyncio.to_thread(qdrant_client.get_collections)
    )

    # Store clients in app state
    app.state.s3_client = s3_client
    app.state.redis_client = redis_client
    app.state.qdrant_client = qdrant_client
    
    yield
    # Cleanup here
    logger.info("Cleaning up services...")
    
    # Close clients
    # NOTE: minio client doesn't need explicit closing
    await app.state.redis_client.aclose()
    app.state.qdrant_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(documents.router)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}

@app.get("/health/deps")
async def health_deps(request: Request):
    """
    Readiness: can we actually reach the object store, redis, and qdrant?
    """
    results = {}

    try:
        await asyncio.to_thread(request.app.state.s3_client.bucket_exists, settings.s3_bucket_raw)
        results["s3"] = "up"
    except Exception as e:
        results["s3"] = f"down: {str(e)}"
    
    try:
        await request.app.state.redis_client.ping()
        results["redis"] = "up"
    except Exception as e:
        results["redis"] = f"down: {str(e)}"
    
    try:
        await asyncio.to_thread(request.app.state.qdrant_client.get_collections)
        results["qdrant"] = "up"
    except Exception as e:
        results["qdrant"] = f"down: {str(e)}"
    
    if any(v != "up" for v in results.values()):
        raise HTTPException(status_code=503, detail=results)
    
    return results