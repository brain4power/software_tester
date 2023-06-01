import os

from django.conf import settings

from kombu import Queue, Exchange
from celery import Celery

__all__ = ["celery_app"]

# get environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# create celery app
celery_app = Celery("core_app", backend=settings.CELERY_RESULT_BACKEND, broker=settings.CELERY_BROKER_URL)

CELERY_ENABLE_UTC = getattr(settings, "CELERY_ENABLE_UTC", True)
# reconfig app with django settings
celery_app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    enable_utc=CELERY_ENABLE_UTC,
)

DEFAULT_QUEUE = settings.APP_CELERY_DEFAULT_QUEUE

celery_app.conf.update(
    task_queues=tuple([Queue(q, exchange=Exchange(q), routing_key=q) for q in settings.APP_CELERY_TASK_QUEUES]),
    task_default_queue=DEFAULT_QUEUE,
    task_default_exchange=DEFAULT_QUEUE,
    task_default_routing_key=DEFAULT_QUEUE,
)

# routes
celery_app.conf.task_routes = {
    # dispatch with tasks itself
}

# beat tasks
celery_app.conf.beat_schedule = {}
