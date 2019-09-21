from django.core.management.base import BaseCommand
from magi import urls # Unused, ensures RAW_CONTEXT is filled
from magi.tools import generateMap

class Command(BaseCommand):
    def handle(self, *args, **options):
        generateMap()
