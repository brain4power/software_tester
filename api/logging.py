import logging

# Lamb Framework
from lamb.utils import get_current_request

__all__ = ["AppContextFilter"]

logger = logging.getLogger(__name__)


class AppContextFilter(logging.Filter):
    def filter(self, record):
        r = get_current_request()  # type:

        try:
            record.app_user_id = r.app_user_id
        except:
            record.app_user_id = None

        try:
            _xray = r.xray
        except:
            _xray = None

        record.xray = _xray
        return True
