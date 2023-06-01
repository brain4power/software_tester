import os
import csv
import json
import logging
import importlib
from typing import Dict, Callable, Optional
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.hashers import make_password

# Lamb Framework
from lamb.db.session import lamb_db_session_maker
from lamb.management.base import LambCommand

# Project
from api.models import *

logger = logging.getLogger(__name__)


@dataclass
class _HandbookLoadRule(object):
    handbook_class: object
    data_file_name: str
    transformers_map: Optional[Dict[str, Callable]] = None
    delimiter: str = ";"
    icons_loader: Optional[Callable] = None
    force_remove: bool = False
    post_processor: Optional[Callable] = None


@dataclass
class _HandbookLoadJSONRule(object):
    class_map: dict
    data_file_name: str
    transformers_map: Optional[Dict[str, Callable]] = None
    force_remove: bool = False
    post_processor: Optional[Callable] = None


class Command(LambCommand):
    help = "Fill database with test handbooks values"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_session = lamb_db_session_maker()
        self.handbooks_folder = os.path.join(settings.LAMB_SYSTEM_STATIC_FOLDER, "handbooks")

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-e",
            "--exclude",
            action="store",
            dest="exclude",
            default=None,
            help="Handbook classes to exclude from filling",
            type=str,
        )
        parser.add_argument(
            "-i",
            "--include",
            action="store",
            dest="include",
            default=None,
            help="Handbook classes to exclusively include for filling",
            type=str,
        )
        parser.add_argument(
            "-f",
            "--forced",
            action="store",
            dest="forced",
            default=None,
            help="Handbook classes to force cleanup before filling",
        )
        parser.add_argument(
            "--without-icons", action="store_true", dest="without_icons", help="Flag to avoid icons parsing"
        )

    def __add_from_csv(self, filling_rule: _HandbookLoadRule):
        # prepare
        logger.info(f"Filling handbooks info for {filling_rule.handbook_class} from {filling_rule.data_file_name}")
        _model_class = filling_rule.handbook_class
        _file_name = filling_rule.data_file_name
        _transformers = filling_rule.transformers_map or {}
        _delimiter = filling_rule.delimiter
        _force_remove = filling_rule.force_remove
        _post_processor = filling_rule.post_processor

        # remove if required
        if _force_remove:
            self.db_session.query(_model_class).delete()

        # process
        file_path = os.path.join(self.handbooks_folder, _file_name)
        with open(file_path, encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=_delimiter)
            for row in csv_reader:
                r = _model_class()
                for field in csv_reader.fieldnames:
                    if len(row[field]) > 0:
                        v = row[field]
                        if field in _transformers:
                            v = _transformers[field](v)
                        setattr(r, field, v)
                self.db_session.add(r)
                self.db_session.flush([r])
                if _post_processor is not None:
                    _post_processor(r, row)

    def __add_from_json(self, filling_rule: _HandbookLoadJSONRule):
        # prepare
        logger.info(f"Filling handbooks info for {filling_rule.class_map} from {filling_rule.data_file_name}")
        _class_map = filling_rule.class_map
        _file_name = filling_rule.data_file_name
        _transformers = filling_rule.transformers_map or {}
        _force_remove = filling_rule.force_remove
        _post_processor = filling_rule.post_processor

        # remove if required
        if _force_remove:
            for model_class in _class_map.values():
                self.db_session.query(model_class).delete()

        # process
        file_path = os.path.join(self.handbooks_folder, _file_name)
        with open(file_path, encoding="utf-8") as json_file:
            all_data = json.loads(json_file.read())
            for object_data in all_data:
                initiated_class = _class_map[object_data.pop("_class_name")]()
                related_objects_data = object_data.pop("_related")
                # fill attributes
                for attr_name, value in object_data.items():
                    if attr_name in _transformers:
                        value = _transformers[attr_name](value)
                    setattr(initiated_class, attr_name, value)
                self.db_session.add(initiated_class)
                self.db_session.flush()
                # create related objects
                for related_data in related_objects_data:
                    related_class = _class_map[related_data.pop("_class_name")]()
                    _reference_from = related_data.pop("_reference_from")
                    _reference_to = related_data.pop("_reference_to")
                    setattr(related_class, _reference_from, getattr(initiated_class, _reference_to))
                    for attr_name, value in related_data.items():
                        if attr_name in _transformers:
                            value = _transformers[attr_name](value)
                        setattr(related_class, attr_name, value)
                    self.db_session.add(related_class)
                    self.db_session.flush()

    def handle(self, *args, **options):
        # prepare default rules
        filling_rules = [
            # core
            _HandbookLoadRule(
                SuperAdmin,
                "super_admins.csv",
                transformers_map={
                    "password_hash": make_password,
                    "is_email_confirmed": lambda x: x == "TRUE",
                    "is_confirmed": lambda x: x == "TRUE",
                },
            ),
        ]  # type: # List[_HandbookLoadRule]

        # check params
        api_model_module = importlib.import_module("api.models")

        def parse_handbook_classes(arg_value):
            result = arg_value.split(",")
            result = ["".join(c.split()) for c in result]
            result = [getattr(api_model_module, c) for c in result]
            return result

        include_classes = options["include"]
        if include_classes is not None:
            include_classes = parse_handbook_classes(include_classes)
            filling_rules = [hr for hr in filling_rules if hr.handbook_class in include_classes]

        excluded_classes = options["exclude"]
        if excluded_classes is not None:
            excluded_classes = parse_handbook_classes(excluded_classes)
            filling_rules = [hr for hr in filling_rules if hr.handbook_class not in excluded_classes]

        forced_remove_classes = options["forced"]
        if forced_remove_classes is not None:
            forced_remove_classes = parse_handbook_classes(forced_remove_classes)
            for f_rule in filling_rules:
                f_rule.force_remove = f_rule.handbook_class in forced_remove_classes

        logger.info(f"final handbooks filling rules to fill: {filling_rules}")

        # parse handbooks data
        for f_rule in filling_rules:
            if isinstance(f_rule, _HandbookLoadJSONRule):
                self.__add_from_json(f_rule)
            else:
                self.__add_from_csv(f_rule)
            self.db_session.flush()

        # flush changes
        self.db_session.commit()
