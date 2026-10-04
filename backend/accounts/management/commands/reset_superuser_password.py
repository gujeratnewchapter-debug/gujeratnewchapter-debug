import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Safely reset the password for the existing active superuser without creating any new user.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--identifier',
            required=True,
            help='Username of the existing superuser to reset.',
        )
        parser.add_argument(
            '--password-env',
            dest='password_env',
            required=True,
            help='Environment variable name that contains the temporary password.',
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        env_name = options['password_env']

        User = get_user_model()

        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            raise CommandError(f'No user found for username: {identifier}')

        if not user.is_superuser:
            raise CommandError(f'User {identifier} is not a superuser.')

        if not user.is_active:
            raise CommandError(f'User {identifier} is not active.')

        password = os.environ.get(env_name)
        if not password or not password.strip():
            raise CommandError(f'Environment variable {env_name} is missing or empty.')

        user.set_password(password)
        user.save(update_fields=['password'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully reset password for active superuser: {identifier}'
            )
        )
