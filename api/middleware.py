import uuid
import logging
from typing import Type, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse

# Lamb Framework
from lamb.exc import ServerError, AuthCredentialsExpired, AuthCredentialsInvalid
from lamb.utils import LambRequest
from lamb.utils.transformers import transform_uuid

import jwt

# Project
from api.utils import AppRequest
from api.models import AbstractUser

logger = logging.getLogger(__name__)

__all__ = [
    "AppAuthMiddleware",
]


class _LazyHttpRequestDescriptor:
    """Abstract lazy request descriptor

    Descriptor logic required cause lazy, lazy_proxy_object, SimpleLazyObject returns different proxy-kind functions.
    This proxy functions is not evaluated on first access until deferred fields/methods/meta invoked.

    Important notes:
    - self: is descriptor instance itself, single for all instances of class and class level itself
    - instance: is actual instance of bounded class  (a.x) or bounded  class (A.x)
    - owner: bounded class (A)

    """

    def __init__(self, factory):
        """Factory is callable that accept single request arg"""
        self.__factory__ = factory

    def __set_name__(self, owner, name):
        """Need explicit name binding in case of several lazy objects used on request instance"""
        _private_name = "_" + name
        self._private_name = _private_name

    def __get__(self, instance, owner):
        """Applicable both to instances and class"""
        # access class level descriptor info - return descriptor itself
        if instance is None:
            return self

        # access instance level descriptor info - check and return unwrapped/factored instance
        if not isinstance(instance, HttpRequest):
            raise ServerError("Invalid instance object for lazy factory apply")
        if not hasattr(instance, self._private_name):
            instance.__dict__[self._private_name] = self.__factory__(instance)
        return instance.__dict__[self._private_name]

    def __set__(self, instance, value):
        """Applicable only to instances"""
        instance.__dict__[self._private_name] = value


def _get_user_token_from_headers(
    request: AppRequest,
) -> Optional[str]:
    """Extracts token from request"""
    try:
        return request.META["HTTP_X_LAMB_AUTH_TOKEN"]
    except (AttributeError, KeyError):
        return None


def _get_user_token_payload(
    request: AppRequest,
) -> dict:
    """Extracts payload from token"""
    try:
        return jwt.decode(request.app_user_token, settings.APP_JWT_SECRET_KEY, algorithms=[settings.APP_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise AuthCredentialsExpired() from e
    except (jwt.DecodeError, jwt.InvalidSignatureError, jwt.InvalidAlgorithmError) as e:
        raise AuthCredentialsInvalid() from e


def _get_user_id(
    request: AppRequest,
) -> uuid.UUID:
    """Extracts user_id from token payload"""
    return transform_uuid(request.app_user_token_payload.get("user_id"))


def _get_user(
    request: AppRequest,
) -> Type[AbstractUser]:
    """Give User object by user_id"""
    user_id = request.app_user_id
    user = request.lamb_db_session.query(AbstractUser).filter(AbstractUser.user_id == transform_uuid(user_id)).first()
    if user is None:
        raise AuthCredentialsInvalid()
    return user


class AppAuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: LambRequest) -> HttpResponse:
        request_cls = request.__class__

        # attach user_token
        if not hasattr(request_cls, "app_user_token"):
            # attach descriptor on first usage for  every request class
            descr = _LazyHttpRequestDescriptor(factory=_get_user_token_from_headers)
            descr.__set_name__(request_cls, "app_user_token")
            request_cls.app_user_token = descr

        # attach user_token_payload
        if not hasattr(request_cls, "app_user_token_payload"):
            # attach descriptor on first usage for  every request class
            descr = _LazyHttpRequestDescriptor(factory=_get_user_token_payload)
            descr.__set_name__(request_cls, "app_user_token_payload")
            request_cls.app_user_token_payload = descr

        # attach user_id
        if not hasattr(request_cls, "app_user_id"):
            # attach descriptor on first usage for  every request class
            descr = _LazyHttpRequestDescriptor(factory=_get_user_id)
            descr.__set_name__(request_cls, "app_user_id")
            request_cls.app_user_id = descr

        # attach user
        if not hasattr(request_cls, "app_user"):
            # attach descriptor on first usage for  every request class
            descr = _LazyHttpRequestDescriptor(factory=_get_user)
            descr.__set_name__(request_cls, "app_user")
            request_cls.app_user = descr

        response = self.get_response(request)
        return response
