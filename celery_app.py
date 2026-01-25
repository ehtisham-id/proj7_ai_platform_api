from celery import Celery
from app.core.config import settings
from kombu import Queue

app = Celery('ai_platform')
app.conf.update(
    broker_url=settings.RABBITMQ_URL,
    result_backend=settings.REDIS_URL,
    task_routes={
        'app.tasks.*': {'queue': 'ai_platform'},
    },
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

app.conf.task_queues = (
    Queue('ai_platform', routing_key='ai_platform.#'),
    Queue('kafka_events', routing_key='kafka.#'),
)
