import uuid
import importlib

from django.conf import settings
from django.core.management import call_command

# SQLAlchemy
from sqlalchemy_utils import drop_database, create_database, database_exists

# Lamb Framework
import lamb.db.session
from lamb.db.session import metadata, lamb_db_session_maker

import pytest

from .factories import *


@pytest.fixture
def db():
    settings.DATABASES["default"]["NAME"] = "test_core"
    importlib.reload(lamb.db.session)
    session = lamb_db_session_maker()

    db_url = session.get_bind().url
    if database_exists(db_url):
        drop_database(db_url)
    create_database(session.get_bind().url)

    session.execute("CREATE EXTENSION pgcrypto")
    session.commit()

    metadata.bind = session.get_bind()
    metadata.create_all()
    # fill_handbooks
    call_command("fill_handbooks")

    session = lamb_db_session_maker()
    AlchemyModelFactory._meta.sqlalchemy_session = session
    yield session
    session.rollback()
    drop_database(db_url)
