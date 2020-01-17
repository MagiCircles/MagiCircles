from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from magi.tools import generateSettings
try:
    CUSTOM_GENERATE_SETTINGS = __import__(django_settings.SITE + '.management.commands.generate_settings', fromlist=[''])
except ImportError:
    CUSTOM_GENERATE_SETTINGS = None

class Command(BaseCommand):
    def handle(self, *args, **options):
        if CUSTOM_GENERATE_SETTINGS:
            CUSTOM_GENERATE_SETTINGS.generate_settings()
        else:
            generateSettings({})
