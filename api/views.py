import logging
from typing import Type, Optional

from django.apps import apps

# Lamb Framework
from lamb.exc import AuthForbidden, NotExistError, InvalidParamValueError
from lamb.json import JsonResponse
from lamb.utils import dpath_value, timed_lru_cache
from lamb.rest.rest_view import RestView
from lamb.rest.decorators import rest_allowed_http_methods

# Project
from api.tasks import store_exchanges_rates_task
from api.utils import AppRequest, get_handbooks_values, get_user_by_identifier
from api.models import *
from api.auth.auth_engines import AbstractAuthEngine, auth_engine_identity_map

__all__ = [
    "AppVersionView",
    "PingView",
    # handbooks
    "HandbooksListView",
    "HandbookView",
    # auth
    "AuthRegisterView",
    # user
    "UserView",
    "StoreExchangeRatesView",
]

logger = logging.getLogger(__name__)


@rest_allowed_http_methods(["GET"])
class AppVersionView(RestView):
    """
    Get installed apps versions
    """

    def get(self, *args, **kwargs) -> dict:
        result = {
            app.name: app.module.__version__ for app in apps.get_app_configs() if hasattr(app.module, "__version__")
        }
        return result


@rest_allowed_http_methods(["GET"])
class PingView(RestView):
    def get(self, request):
        return {"response": "pong"}


@timed_lru_cache(minutes=60)
def _cached_handbooks(request):
    return {
        handbook_name: get_handbooks_values(request, handbook_class)
        for handbook_name, handbook_class in handbook_map.items()
    }


# handbooks
@rest_allowed_http_methods(["GET"])
class HandbooksListView(RestView):
    def get(self, request: AppRequest):
        return _cached_handbooks(request)


@rest_allowed_http_methods(["GET"])
class HandbookView(RestView):
    def get(self, request: AppRequest, handbook_name: str):
        if handbook_name not in handbook_map:
            raise NotExistError(f"Handbook with name {handbook_name} does not exists")
        return get_handbooks_values(request, handbook_map[handbook_name])


# authorize
def _get_auth_engine(parsed_body: dict) -> Optional[Type[AbstractAuthEngine]]:
    """Extracts authentication engine from request body"""
    engine_name = dpath_value(parsed_body, "engine", str, transform=lambda x: x.lower())
    try:
        return auth_engine_identity_map[engine_name]
    except KeyError:
        raise InvalidParamValueError(f"Unknown auth engine='{engine_name}'")


@rest_allowed_http_methods(["POST"])
class AuthRegisterView(RestView):
    def post(self, request: AppRequest):
        """User authentication/registration view"""
        # extract and check params
        engine_class = _get_auth_engine(self.parsed_body)
        credentials = dpath_value(self.parsed_body, "credentials", dict)
        engine = engine_class(request.lamb_db_session)
        # authenticate user
        access_token, refresh_token, user = engine.authenticate(credentials)
        request.app_user_token = access_token
        request.app_user = user
        request.lamb_db_session.commit()
        # return result
        result = JsonResponse(
            status=200,
            data={
                "access_token": access_token,
                "user": user,
            },
            request=request,
        )
        result.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="strict")
        return result


@rest_allowed_http_methods(["GET"])
class UserView(RestView):
    def get(self, request: AppRequest, user_id: str):
        """
        User details
        """
        user = get_user_by_identifier(request, user_id)  # type: Type[AbstractUser]
        if not request.app_user.can_read_user(user):
            raise AuthForbidden(f"You have not access to user with user_id: {user_id}")

        return user


@rest_allowed_http_methods(["POST"])
class StoreExchangeRatesView(RestView):
    def post(self, request: AppRequest):
        if not isinstance(request.app_user, (SuperAdmin, Operator)):
            raise AuthForbidden("You have not access to store exchanges rates.")
        store_exchanges_rates_task.apply_async((request.app_user_id,))
        return JsonResponse(status=201)
