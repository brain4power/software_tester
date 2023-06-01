from typing import Dict, Type

from .email import EmailAuthEngine
from .abstract import AbstractAuthEngine

__all__ = ["AbstractAuthEngine", "EmailAuthEngine", "auth_engine_identity_map"]

auth_engine_identity_map = {
    e.__identity__.lower(): e
    for e in [
        EmailAuthEngine,
    ]
}  # type: Dict[str, Type[AbstractAuthEngine]]
