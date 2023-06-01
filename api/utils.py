import enum
import logging

from django.conf import settings

# Lamb Framework
from lamb.exc import NotExistError
from lamb.utils import LambRequest
from lamb.ext.settings import AbstractSettingsValue
from lamb.utils.transformers import transform_uuid

import redis

# Project
from api.models import *

__all__ = [
    "AppRequest",
    "get_handbooks_values",
    "redis_throttling_node",
    "get_user_by_identifier",
]

logger = logging.getLogger(__name__)


class AppRequest(LambRequest):
    """
    Class used only for proper type hinting in pycharm, does not guarantee that properties will exist
    """

    def __init__(self):
        super(AppRequest, self).__init__()
        self.app_user_token = None
        self.app_user_token_payload = None
        self.app_user_id = None
        self.app_user = None


def get_handbooks_values(request, handbook_class):
    if issubclass(handbook_class, AbstractSettingsValue):
        return handbook_class.get_visible_configs()
    elif isinstance(handbook_class, enum.EnumMeta):
        return [handbook_class.__members__[key].value for key in list(handbook_class.__members__)]
    else:
        return request.lamb_db_session.query(handbook_class).filter(handbook_class.is_actual == True).all()


def redis_throttling_node() -> redis.Redis:
    return redis.from_url(settings.APP_REDIS_THROTTLING_NODE)


def get_user_by_identifier(request: AppRequest, user_id: str):
    if user_id == "me":
        return request.app_user
    user_id = transform_uuid(user_id)
    user = request.lamb_db_session.query(AbstractUser).get(user_id)
    if user is None:
        raise NotExistError(f"User with user_id: {user_id} does not exists")
    return user
