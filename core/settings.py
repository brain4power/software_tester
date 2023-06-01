import json
import os
import logging
import warnings
from pathlib import Path
from urllib.parse import urljoin

# Lamb Framework
from lamb.json import JsonEncoder

from lamb.utils import dpath_value, get_redis_url, compact
from lamb.utils.validators import validate_port
from lamb.utils.transformers import tf_list_string, transform_boolean

import urllib3.exceptions

logging.captureWarnings(True)
warnings.filterwarnings("default", category=DeprecationWarning, module="django")
warnings.filterwarnings("default", category=DeprecationWarning, module="lamb")
warnings.filterwarnings("default", category=DeprecationWarning, module="core")
warnings.filterwarnings("default", category=urllib3.exceptions.InsecureRequestWarning, module="urllib3")

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = dpath_value(os.environ, "APP_API_SECRET_KEY", str)

# Static folders and urls
LAMB_STATIC_FOLDER = os.path.join(BASE_DIR, "static/")
LAMB_SYSTEM_STATIC_FOLDER = os.path.join(BASE_DIR, "system-static/")
LAMB_TEMPLATES_FOLDER = os.path.join(LAMB_SYSTEM_STATIC_FOLDER, "templates/")
LAMB_IMAGE_UPLOAD_ENGINE = "lamb.service.image.uploaders.ImageUploadServiceDisk"

STATIC_URL = "/static/"

LAMB_RUN_FOLDER = os.path.join(BASE_DIR, "run")
LAMB_TMP_FOLDER = os.path.join(BASE_DIR, "tmp")
LAMB_LOG_FOLDER = os.path.join(BASE_DIR, "log")
LAMB_CRT_FOLDER = os.path.join(BASE_DIR, "crt")
LAMB_BKP_FOLDER = os.path.join(BASE_DIR, "bkp")

PORT = dpath_value(os.environ, "APP_API_PORT", int)
DEBUG = dpath_value(os.environ, "APP_DEBUG", str, transform=transform_boolean, default=False)
SCHEME = dpath_value(os.environ, "APP_API_SCHEME", str)
ALLOWED_HOSTS = dpath_value(os.environ, "APP_ALLOWED_HOSTS", str, transform=tf_list_string)
HOST = ALLOWED_HOSTS[0]

# config host and port
STATIC_HOST = HOST
if PORT not in [80, 443]:
    STATIC_HOST = f"{STATIC_HOST}:{PORT}"

# config static folder urls
LAMB_STATIC_URL = urljoin(f"{SCHEME}://{STATIC_HOST}", "/static/")
LAMB_SYSTEM_STATIC_URL = urljoin(f"{SCHEME}://{STATIC_HOST}", "/system-static/")
# Application definition

INSTALLED_APPS = [
    "lamb",
    "api",
]

LAMB_RESPONSE_APPLY_TO_APPS = [
    "api",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "lamb.middleware.grequest.LambGRequestMiddleware",
    "lamb.middleware.cors.LambCorsMiddleware",
    "lamb.middleware.xray.LambXRayMiddleware",
    "lamb.middleware.device_info.LambDeviceInfoMiddleware",
    "lamb.middleware.db.LambSQLAlchemyMiddleware",
    "api.middleware.AppAuthMiddleware",
    "lamb.middleware.rest.LambRestApiJsonMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [LAMB_TEMPLATES_FOLDER],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# redis
APP_REDIS_BASE_HOST = dpath_value(os.environ, "APP_REDIS_BASE_HOST", str)
APP_REDIS_BASE_PORT = dpath_value(os.environ, "APP_REDIS_BASE_PORT", int, transform=validate_port)
APP_REDIS_BASE_PASS = dpath_value(os.environ, "APP_REDIS_BASE_PASS", str)

CELERY_BROKER_URL = get_redis_url(
    host=APP_REDIS_BASE_HOST, port=APP_REDIS_BASE_PORT, password=APP_REDIS_BASE_PASS, db=0
)
CELERY_RESULT_BACKEND = get_redis_url(
    host=APP_REDIS_BASE_HOST, port=APP_REDIS_BASE_PORT, password=APP_REDIS_BASE_PASS, db=0
)
APP_REDIS_THROTTLING_NODE = get_redis_url(
    host=APP_REDIS_BASE_HOST, port=APP_REDIS_BASE_PORT, password=APP_REDIS_BASE_PASS, db=1
)

# Database
DB_USER = dpath_value(os.environ, "APP_POSTGRES_USER", str)
DB_HOST = dpath_value(os.environ, "APP_POSTGRES_HOST", str)
DB_PASS = dpath_value(os.environ, "APP_POSTGRES_PASSWORD", str, default="")
DB_NAME = dpath_value(os.environ, "APP_POSTGRES_DB_NAME", str)
DB_ENGINE = dpath_value(os.environ, "APP_DB_ENGINE", str)
DB_CONNECT_OPTS = dpath_value(os.environ, "APP_POSTGRES_CONNECT_OPTS", str, default=None)
DB_PORT = dpath_value(os.environ, "APP_POSTGRES_PORT", int, default=None)

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASS,
        "HOST": DB_HOST,
        "CONNECT_OPTS": DB_CONNECT_OPTS,
        "PORT": DB_PORT,
    },
}
APP_NAME = dpath_value(os.environ, "APP_NAME", str, default=None)

# loggers
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s: xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)8s] <%(name)s:%(filename)s:%(lineno)4d>  %(message)s "
        },
        "simple": {"format": "[%(asctime)s: xray=%(xray)s, user_id=%(app_user_id)s: %(levelname)8s] %(message)s"},
    },
    "filters": {"app_context": {"()": "api.logging.AppContextFilter"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "filters": ["app_context"],
        },
        "api_log_file": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LAMB_LOG_FOLDER, "api.log"),
            "when": "midnight",
            "backupCount": 30,
            "formatter": "verbose",
            "filters": ["app_context"],
        },
        "lamb_log_file": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LAMB_LOG_FOLDER, "lamb.log"),
            "when": "midnight",
            "backupCount": 30,
            "formatter": "verbose",
            "filters": ["app_context"],
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "propagate": True, "level": "INFO"},
        "api": {"handlers": ["api_log_file", "console"], "propagate": True, "level": "DEBUG"},
        "lamb": {"handlers": ["lamb_log_file", "console"], "propagate": True, "level": "INFO"},
        "services": {"handlers": ["api_log_file", "console"], "propagate": True, "level": "DEBUG"},
        "py.warnings": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True
# Lamb Framework
# lamb
from lamb.utils.logging import inject_logging_factory  # noqa: E402

LAMB_LOG_LINES_FORMAT = "PREFIX"
inject_logging_factory()

LAMB_ADD_CORS_ENABLED = False
LAMB_RESPONSE_DATE_FORMAT = "%m.%d.%Y"
LAMB_DEVICE_DEFAULT_LOCALE = "en_US"
LAMB_DEVICE_INFO_CLASS = "lamb.types.device_info.DeviceInfo"
LAMB_DEVICE_INFO_COLLECT_IP = True
LAMB_DEVICE_INFO_COLLECT_GEO = False
LAMB_DEVICE_INFO_HEADER_FAMILY = "HTTP_X_LAMB_DEVICE_FAMILY"
LAMB_DEVICE_INFO_HEADER_PLATFORM = "HTTP_X_LAMB_DEVICE_PLATFORM"
LAMB_DEVICE_INFO_HEADER_OS_VERSION = "HTTP_X_LAMB_DEVICE_OS_VERSION"
LAMB_DEVICE_INFO_HEADER_LOCALE = "HTTP_X_LAMB_DEVICE_LOCALE"
LAMB_DEVICE_INFO_HEADER_APP_VERSION = "HTTP_X_LAMB_APP_VERSION"
LAMB_DEVICE_INFO_HEADER_APP_BUILD = "HTTP_X_LAMB_APP_BUILD"
LAMB_DEVICE_INFO_HEADER_APP_ID = "HTTP_X_LAMB_APP_ID"
LAMB_DEVICE_INFO_LOCALE_VALID_SEPS = ("_", "-")
LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL = logging.INFO
LAMB_EXECUTION_TIME_SKIP_METHODS = "OPTIONS"
LAMB_ERROR_OVERRIDE_PROCESSOR = None
LAMB_RESPONSE_ENCODER = "lamb.json.encoder.JsonEncoder"
LAMB_RESPONSE_DATETIME_TRANSFORMER = "lamb.utils.transformers.transform_datetime_seconds_int"
LAMB_RESPONSE_JSON_INDENT = None

LAMB_PAGINATION_LIMIT_DEFAULT = 100
LAMB_PAGINATION_LIMIT_MAX = 5000
LAMB_PAGINATION_KEY_OFFSET = "offset"
LAMB_PAGINATION_KEY_LIMIT = "limit"
LAMB_PAGINATION_KEY_ITEMS = "items"
LAMB_PAGINATION_KEY_ITEMS_EXTENDED = "items_extended"
LAMB_PAGINATION_KEY_TOTAL = "total_count"
LAMB_PAGINATION_KEY_OMIT_TOTAL = "total_omit"

LAMB_SORTING_KEY = "sorting"

# celery queues
APP_CELERY_DEFAULT_QUEUE = "default"

APP_CELERY_TASK_QUEUES = [APP_CELERY_DEFAULT_QUEUE]
APP_CELERY_TASK_TIMEOUT = 10

# auth
APP_JWT_SECRET_KEY = dpath_value(os.environ, "APP_JWT_SECRET_KEY", str)
APP_JWT_ALGORITHM = "HS256"

APP_MOCKING = dpath_value(os.environ, "APP_MOCKING", str, transform=transform_boolean, default=False)
APP_EXCHANGE_RATES_API_URL = dpath_value(os.environ, "APP_EXCHANGE_RATES_API_URL", str)
