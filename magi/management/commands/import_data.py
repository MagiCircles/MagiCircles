from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Load dynamic module based on SITE

import_data_module = __import__(settings.SITE + '.import_data', fromlist=[''])

class Command(BaseCommand):
    def handle(self, *args, **options):
        options = ['verbose', 'local']
        kwargs = { 'to_import': [] }
        for arg in args:
            if arg in options:
                kwargs[arg] = True
            else:
                kwargs['to_import'].append(arg)
        if not kwargs['to_import']:
            kwargs['to_import'] = None

        import_data_module.import_data(**kwargs)
