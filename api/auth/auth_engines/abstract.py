import logging
from uuid import UUID
from datetime import datetime, timedelta

from django.conf import settings

# SQLAlchemy
from sqlalchemy.orm.session import Session as SASession

# Lamb Framework
from lamb.exc import ServerError, NotAllowedMethodError, NotRealizedMethodError

import jwt

# Project
from api.models import SettingsValue

logger = logging.getLogger(__name__)

__all__ = [
    "AbstractAuthEngine",
]


class AbstractAuthEngine(object):
    __identity__ = None

    def __init__(self, db_session):
        """
        :type db_session: sqlalchemy.orm.session.Session
        """
        self.db_session = db_session
        if not isinstance(self.db_session, SASession):
            logger.warning(f"Auth engine {self.__class__.__name__} initiated without database session")
            raise ServerError("Improperly configured auth engine")

    @staticmethod
    def _create_token_pair(
        user_id: UUID,
    ) -> tuple[str, str]:
        user_id_str = str(user_id)
        access_token = jwt.encode(
            {
                "user_id": user_id_str,
                "exp": datetime.utcnow() + timedelta(minutes=SettingsValue.access_token_timeout.val),
            },
            settings.APP_JWT_SECRET_KEY,
            algorithm=settings.APP_JWT_ALGORITHM,
        )
        refresh_token = jwt.encode(
            {
                "user_id": user_id_str,
                "exp": datetime.utcnow() + timedelta(minutes=SettingsValue.refresh_token_timeout.val),
            },
            settings.APP_JWT_SECRET_KEY,
            algorithm=settings.APP_JWT_ALGORITHM,
        )
        return access_token, refresh_token

    def authenticate(self, credentials):
        """Authenticate user with provided credentials
        :type credentials: dict
        :return: MephiUser
        """
        raise NotRealizedMethodError(f"Authenticate operation with engine '{self.__identity__}' not realized yet")

    def register_user(self, credentials):
        """Register new user with provided credentials
        :type credentials: dict
        :return: MephiUser
        """
        raise NotRealizedMethodError(f"Register operation with engine '{self.__identity__}' not realized yet")

    def resend_confirm(self, credentials):
        """Resent confirmation information
        :type credentials: dict
        :return: None
        """
        raise NotAllowedMethodError(f"Resend confirm operation with engine '{self.__identity__}' not supported")

    def confirm(self, confirmation_code):
        """Confirm created user credentials
        :type confirmation_code: str
        :return: None
        """
        raise NotAllowedMethodError(f"Confirm operation with engine '{self.__identity__}' not supported")

    def restore_request(self, credentials):
        """Credentials restore request
        :type credentials: dict
        :return: None
        """
        raise NotAllowedMethodError(f"Restore request operation with engine '{self.__identity__}' not supported")

    def restore_confirm(self, credentials, restore_code):
        """Credentials restore confirm
        :type credentials: dict
        :type restore_code: str
        :return: None
        """
        raise NotAllowedMethodError(f"Restore confirm operation with engine '{self.__identity__}' not supported")

    @classmethod
    def bounded(cls, user) -> bool:
        """Check for credentials to this engine"""
        raise NotRealizedMethodError(f"User engine bounding not implemented on '{cls.__identity__}'")
