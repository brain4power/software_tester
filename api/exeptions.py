from enum import IntEnum, unique

# Lamb Framework
from lamb.exc import *

__all__ = [
    "UserIsNotConfirmedError",
    "UserIsBlockedError",
]


@unique
class AppExceptionCodes(IntEnum):
    # core
    UserIsNotConfirmed = 1001
    UserIsBlocked = 1002


class UserIsNotConfirmedError(ClientError):
    """do anything until user is confirmed"""

    _app_error_code = AppExceptionCodes.UserIsNotConfirmed
    _status_code = 403
    _message = "Can not do anything until the user is confirmed"


class UserIsBlockedError(ClientError):
    """do anything until user is blocked"""

    _app_error_code = AppExceptionCodes.UserIsBlocked
    _status_code = 403
    _message = "Can not do anything until the user is blocked"
