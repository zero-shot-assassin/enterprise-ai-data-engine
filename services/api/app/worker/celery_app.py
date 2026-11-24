from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "eade-worker+--",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_ack_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
)