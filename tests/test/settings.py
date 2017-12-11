from django.conf import settings as django_settings
from test import models

SITE_NAME = 'Sample Website'
SITE_URL = 'http://test.com/'
SITE_IMAGE = 'test.png'
SITE_STATIC_URL = '//localhost:{}/'.format(django_settings.DEBUG_PORT) if django_settings.DEBUG else '//i.test.com/'
GAME_NAME = 'Sample Game'
DISQUS_SHORTNAME = 'test'
ACCOUNT_MODEL = models.Account
COLOR = '#4a86e8'
