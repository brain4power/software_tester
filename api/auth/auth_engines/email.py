import logging
from typing import Type, Optional

# Lamb Framework
from lamb.exc import AuthCredentialsInvalid
from lamb.utils import dpath_value

# Project
from api.models import AbstractUser, RefreshToken

from .abstract import *

logger = logging.getLogger(__name__)


class EmailAuthEngine(AbstractAuthEngine):
    __identity__ = "email"

    def _get_info(self, credentials: dict, requires_password=True) -> tuple[str, str, Optional[Type[AbstractUser]]]:
        """Parse common params for engine and try to find user in database
        :type credentials: dict
        :type requires_password: bool
        :return: (str, str, AbstractUser)
        """
        # check params
        email = dpath_value(credentials, "email", str).lower()
        if requires_password:
            password = dpath_value(credentials, "password", str)
        else:
            password = dpath_value(credentials, "password", str, default=None)

        # extract and check user
        user = self.db_session.query(AbstractUser).filter(AbstractUser.email == email).first()
        return email, password, user

    def authenticate(self, credentials: dict) -> tuple[str, str, Type[AbstractUser]]:
        """Authenticate user with provided credentials
        :type credentials: dict
        :return: Type[AbstractUser]
        """
        # get info
        email, password, user = self._get_info(credentials)

        # process info
        if user is None:
            raise AuthCredentialsInvalid("User password or email is not valid")
        # check password
        if not user.check_password(raw_password=password):
            raise AuthCredentialsInvalid("User password or email is not valid")
        # make tokens
        user_id = user.user_id
        access_token, refresh_token = self._create_token_pair(user_id=user_id)
        token = RefreshToken()
        token.user_id = user_id
        token.value = refresh_token
        self.db_session.add(token)
        self.db_session.commit()
        return access_token, refresh_token, user

    @classmethod
    def bounded(cls, user) -> bool:
        return user.email is not None
