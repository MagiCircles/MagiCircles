from django.conf import settings as django_settings
from sample import models

# Configure and personalize your website here.

SITE_NAME = 'Sample Website'
SITE_URL = 'http://sample.com/'
SITE_IMAGE = 'sample.png'
SITE_STATIC_URL = '//localhost:{}/'.format(django_settings.DEBUG_PORT) if django_settings.DEBUG else '//i.sample.com/'
GAME_NAME = 'Sample Game'
DISQUS_SHORTNAME = 'sample'
ACCOUNT_MODEL = models.Account
COLOR = '#4a86e8'
