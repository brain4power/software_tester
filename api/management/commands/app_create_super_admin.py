import logging

from django.core.management.base import CommandError

# Lamb Framework
from lamb.exc import AlreadyExistError
from lamb.management.base import LambCommand

# Project
from api.models import *

logger = logging.getLogger(__name__)


class Command(LambCommand):
    help = "Create super admin user utility"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "-W", "--password", action="store", dest="password", help="Password value", type=str, required=True
        )
        parser.add_argument("-E", "--email", action="store", dest="email", help="Email value", type=str, required=True)
        parser.add_argument(
            "--first-name",
            action="store",
            dest="first_name",
            type=str,
        )
        parser.add_argument(
            "--last-name",
            action="store",
            dest="last_name",
            type=str,
        )

    def handle(self, *args, **options):
        # parse params
        email = options["email"].lower()
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]

        # check password
        if len(password) == 0:
            raise CommandError("Invalid password length")
        # check email
        user = self.db_session.query(AbstractUser).filter(AbstractUser.email == email).first()
        if user is not None:
            raise AlreadyExistError("User with provided email already exist")
        # check its the first super admin
        super_admin = self.db_session.query(AbstractUser).filter(AbstractUser.user_type == UserType.SUPER_ADMIN).first()
        if super_admin:
            raise AlreadyExistError(f"Super Admin already exist: {super_admin.email}")
        # create super_admin
        super_admin = SuperAdmin()
        super_admin.email = email
        super_admin.set_password(password)
        super_admin.first_name = first_name
        super_admin.last_name = last_name
        super_admin.is_email_confirmed = True
        super_admin.is_confirmed = True

        self.db_session.add(super_admin)
        self.db_session.commit()

        logger.info(f"SuperAdmin {email} was created.")
