import uuid

from django.conf import settings

# Lamb Framework
from lamb.exc import ServerError
from lamb.utils import dpath_value
from lamb.db.context import lamb_db_context

import requests
from celery.utils.log import get_task_logger
from core.celery_config import celery_app

# Project
from api.models import ExchangeRatesRecord

logger = get_task_logger(__name__)

__all__ = [
    "store_exchanges_rates_task",
]

_DEFAULT_QUEUE = settings.APP_CELERY_DEFAULT_QUEUE


@celery_app.task(
    ignored_result=True,
    queue=_DEFAULT_QUEUE,
)
def store_exchanges_rates_task(actor_id: uuid.UUID) -> None:
    logger.info(f"run store_exchanges_rates_task")
    response = requests.get(settings.APP_EXCHANGE_RATES_API_URL)
    if response.status_code != 200:
        logger.error(f"Get not 200 status_code from APP_EXCHANGE_RATES_API_URL: {settings.APP_EXCHANGE_RATES_API_URL}")
        raise ServerError
    with lamb_db_context() as db_session:
        record = ExchangeRatesRecord()
        record.actor_id = actor_id
        record.rate = dpath_value(response.json(), ["rates", "USD"], float, allow_none=True)
        db_session.add(record)
        db_session.commit()
