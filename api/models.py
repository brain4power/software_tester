import re
import enum
import uuid
import logging
from typing import Type
from functools import wraps

from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password

# SQLAlchemy
from sqlalchemy import Enum, Column, ForeignKey, text
from sqlalchemy.orm import object_session
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm.mapper import validates
from sqlalchemy.dialects.postgresql import UUID, FLOAT, BOOLEAN, VARCHAR

# Lamb Framework
from lamb.exc import ServerError, AuthCredentialsInvalid, InvalidParamValueError
from lamb.db.mixins import TimeMarksMixin
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin
from lamb.ext.settings import AbstractSettingsValue, AbstractSettingsStorage

# Project
from api.exeptions import *

__all__ = [
    # settings
    "SettingsValue",
    "SettingsStorage",
    # handbooks
    "UserType",
    "handbook_map",
    # roles
    "AbstractUser",
    "SuperAdmin",
    "Operator",
    # auth
    "RefreshToken",
    "AccountConfirmationTransport",
    # services
    "ExchangeRatesRecord",
]

logger = logging.getLogger(__name__)


@enum.unique
class SettingsValue(AbstractSettingsValue):
    __table_class__ = "SettingsStorage"

    access_token_timeout = ("access_token_timeout", 60 * 24 * 3, "Access token availability time, min", int, None)
    refresh_token_timeout = ("refresh_token_timeout", 60 * 24 * 30, "Refresh token availability time, min", int, None)

    @classmethod
    def get_visible_configs(cls):
        """Extract client-application visible configs
        :return: dict
        """
        items = [
            cls.access_token_timeout,
            cls.refresh_token_timeout,
        ]

        try:
            items = [
                {
                    "name": i.name,
                    "value": i.val,
                    "description": i.description,
                }
                for i in items
            ]
        except Exception as e:
            logger.error(f"Settings convert failed: {e}")
            raise ServerError("Improperly configured settings values") from e
        return items


class SettingsStorage(AbstractSettingsStorage):
    __tablename__ = "app_utils_settings"


@enum.unique
class UserType(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OPERATOR = "OPERATOR"
    USER = "USER"


@enum.unique
class AccountConfirmationTransport(str, enum.Enum):
    EMAIL = "EMAIL"


handbook_map = {
    "configs": SettingsValue,
    "user_types": UserType,
}


def _validate_string_length(
    value: str, key: str, max_length: int, trimming: bool = True, max_length_required: bool = False
) -> str:
    if value is not None:
        value = value.strip()
        if trimming:
            value = " ".join(value.split())
        if len(value) > max_length:
            raise InvalidParamValueError(
                f"Maximum length exceed for field '{key}'. Maximum length is {max_length} symbols."
            )
        if max_length_required and len(value) != max_length:
            raise InvalidParamValueError(f"Field '{key}' length should be {max_length}.")
    return value


def user_check(checkers, params_checkers: tuple = None):
    def _user_check(func):
        @wraps(func)
        def inner(*args, **kwargs):
            user = args[0]
            for checker in checkers:
                checker(user)
            if params_checkers is not None:
                for params_checker in params_checkers:
                    params_checker(*args)
            return func(*args, **kwargs)

        return inner

    return _user_check


def check_account_confirmed(user):
    if not user.is_confirmed:
        raise UserIsNotConfirmedError()


class AbstractUser(TimeMarksMixin, ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "app_role_abstract_user"

    # columns
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_type = Column(
        Enum(UserType, name="user_type"),
        nullable=False,
        default=UserType.USER,
        server_default=UserType.USER.value,
    )

    # email
    password_hash = Column(VARCHAR, nullable=True)
    email = Column(VARCHAR, nullable=True, unique=True)
    is_email_confirmed = Column(BOOLEAN, nullable=False, default=False, server_default=text("FALSE"))
    # personal
    last_name = Column(VARCHAR, nullable=True)
    first_name = Column(VARCHAR, nullable=True)
    # other
    is_confirmed = Column(BOOLEAN, nullable=False, default=False, server_default=text("FALSE"))
    is_blocked = Column(BOOLEAN, nullable=False, default=False, server_default=text("FALSE"))

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    # methods
    def set_password(self, raw_password):
        """
        Account password setter.
        Will set provided value as new password hash
        :type raw_password: str
        """
        try:
            validate_password(raw_password, user=self)
        except ValidationError as e:
            logger.info(f"User password is invalid. Details: {e.messages}")
            raise InvalidParamValueError(f"Invalid password value", error_details=e.messages) from e
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """
        Account password checking.
        Check is password equal to provided in account. In case of success compare but difference in hashers
        algorithm - will update data in database according to modern hash function.
        :type raw_password: str
        :rtype: bool
        """

        def setter(_raw_password):
            self.set_password(_raw_password)
            try:
                session = object_session(self)
                session.commit()
            except Exception:
                pass

        return check_password(raw_password, self.password_hash, setter)

    def change_password(self, password_old, password_new):
        """
        Updates password for user.
        :type password_old: str
        :type password_new: str
        """
        if self.password_hash is not None and not self.check_password(password_old):
            raise AuthCredentialsInvalid("Invalid old password value")
        self.set_password(password_new)

    @validates("email")
    def validate_name(self, key, value):
        if value is not None and re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value) is None:
            raise InvalidParamValueError(f"Invalid email format for field '{key}'.")
        return value

    @validates("facebook_id", "google_plus_id")
    def validate_social_network_id(self, key, value):
        return _validate_string_length(value, key, 150)

    def response_encode(self, request=None):
        encoded_object = super().response_encode(request)
        encoded_object.pop("password_hash", None)
        # add editable_fields
        return encoded_object

    # meta
    __mapper_args__ = {"polymorphic_on": user_type, "polymorphic_identity": None, "with_polymorphic": "*"}


class SuperAdmin(AbstractUser):
    __tablename__ = "app_role_super_admin"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(AbstractUser.user_id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    # permissions
    @user_check(checkers=(check_account_confirmed,))
    def can_create_user(self, user_type: UserType) -> bool:
        return user_type != UserType.SUPER_ADMIN

    @user_check(checkers=(check_account_confirmed,))
    def can_read_user(self, user: "AbstractUser") -> bool:
        return True

    @user_check(checkers=(check_account_confirmed,))
    def can_edit_user(self, user: "AbstractUser") -> bool:
        return True

    # meta
    __mapper_args__ = {
        "polymorphic_identity": UserType.SUPER_ADMIN,
    }


class Operator(AbstractUser):
    __tablename__ = "app_role_operator"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(AbstractUser.user_id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    # permissions
    @user_check(checkers=(check_account_confirmed,))
    def can_create_user(self, user_type: UserType) -> bool:
        return False

    @user_check(checkers=(check_account_confirmed,))
    def can_read_user(self, user: Type[AbstractUser]) -> bool:
        return user == self

    @user_check(checkers=(check_account_confirmed,))
    def can_edit_user(self, user: Type[AbstractUser]) -> bool:
        return user == self

    def response_encode(self, request=None):
        encoded_object = super().response_encode(request)
        return encoded_object

    # meta
    __mapper_args__ = {
        "polymorphic_identity": UserType.OPERATOR,
        "inherit_condition": (user_id == AbstractUser.user_id),
    }


class RefreshToken(TimeMarksMixin, DeclarativeBase):
    __tablename__ = "app_refresh_token"

    # columns
    value = Column(VARCHAR, primary_key=True)
    user_id = Column(
        UUIDType(binary=False, native=True),
        ForeignKey(AbstractUser.user_id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )


class ExchangeRatesRecord(TimeMarksMixin, DeclarativeBase):
    __tablename__ = "app_exchange_rates_record"

    # columns
    record_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    actor_id = Column(
        UUIDType(binary=False, native=True),
        ForeignKey(AbstractUser.user_id, onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    rate = Column(FLOAT)
