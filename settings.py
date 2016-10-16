from django.utils.translation import ugettext_lazy as _

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = '%no*6sl#g&34vg61&4zs*pjk+gb9_ma-oua!@h1o0wn3fxb!k#'

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'web/locale'),
]

SITE = 'none'
AWS_SES_RETURN_PATH = 'none@no.ne'
STATIC_UPLOADED_FILES_PREFIX = ''

LANGUAGES = (
    ('en', _('English')),
    ('es', _('Spanish')),
    ('ru', _('Russian')),
    ('it', _('Italian')),
    ('fr', _('French')),
    ('de', _('German')),
    ('pl', _('Polish')),
    ('ja', _('Japanese')),
    ('zh-hans', _('Simplified Chinese')),
    ('pt-br', _('Brazilian Portuguese')),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'web',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
)
