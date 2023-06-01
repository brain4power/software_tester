import logging

import factory
from factory.fuzzy import FuzzyText

# Project
from api.models import *

__all__ = ["AlchemyModelFactory", "SuperAdminFactory"]

logger = logging.getLogger(__name__)


def get_or_create(sub_factory):
    """
    Returns first instance of a given factory, create if not exist.
    """

    session = AlchemyModelFactory._meta.sqlalchemy_session
    instance = session.query(sub_factory._meta.model).first()
    if not instance:
        instance = sub_factory()
    return instance


class AlchemyModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Save an instance of the model, using shared DB session."""
        cls._meta.sqlalchemy_session = AlchemyModelFactory._meta.sqlalchemy_session
        cls._meta.sqlalchemy_session_persistence = "commit"
        return super()._create(model_class, *args, **kwargs)


class AbstractUserFactory(AlchemyModelFactory):
    email = FuzzyText(prefix="email@", length=20, suffix="example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class SuperAdminFactory(AbstractUserFactory):
    class Meta:
        model = SuperAdmin
