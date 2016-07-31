from django.conf import settings as django_settings
from web.default_settings import DEFAULT_ENABLED_NAVBAR_LISTS, DEFAULT_ENABLED_COLLECTIONS, DEFAULT_ENABLED_PAGES, RAW_CONTEXT, DEFAULT_JAVASCRIPT_TRANSLATED_TERMS
from django.utils.translation import ugettext_lazy as _, string_concat

settings_module = __import__(django_settings.SITE + '.settings', globals(), locals(), ['*'])

############################################################
# Required settings

SITE_NAME = getattr(settings_module, 'SITE_NAME')
SITE_URL = getattr(settings_module, 'SITE_URL')
SITE_IMAGE = getattr(settings_module, 'SITE_IMAGE')
SITE_STATIC_URL = getattr(settings_module, 'SITE_STATIC_URL')
GAME_NAME = getattr(settings_module, 'GAME_NAME')
ACCOUNT_MODEL = getattr(settings_module, 'ACCOUNT_MODEL')
COLOR = getattr(settings_module, 'COLOR')

############################################################
# Optional settings

if hasattr(settings_module, 'WIKI'):
    WIKI = getattr(settings_module, 'WIKI')
else:
    WIKI = None

if hasattr(settings_module, 'BUG_TRACKER_URL'):
    BUG_TRACKER_URL = getattr(settings_module, 'BUG_TRACKER_URL')
else:
    BUG_TRACKER_URL = None

if hasattr(settings_module, 'SITE_LOGO'):
    SITE_LOGO = getattr(settings_module, 'SITE_LOGO')
else:
    SITE_LOGO = None

if hasattr(settings_module, 'GITHUB_REPOSITORY'):
    GITHUB_REPOSITORY = getattr(settings_module, 'GITHUB_REPOSITORY')
else:
    GITHUB_REPOSITORY = None

if hasattr(settings_module, 'CONTRIBUTE_URL'):
    CONTRIBUTE_URL = getattr(settings_module, 'CONTRIBUTE_URL')
else:
    CONTRIBUTE_URL = None

if hasattr(settings_module, 'CONTACT_EMAIL'):
    CONTACT_EMAIL = getattr(settings_module, 'CONTACT_EMAIL')
else:
    CONTACT_EMAIL = None

if hasattr(settings_module, 'CONTACT_REDDIT'):
    CONTACT_REDDIT = getattr(settings_module, 'CONTACT_REDDIT')
else:
    CONTACT_REDDIT = None

if hasattr(settings_module, 'CONTACT_FACEBOOK'):
    CONTACT_FACEBOOK = getattr(settings_module, 'CONTACT_FACEBOOK')
else:
    CONTACT_FACEBOOK = None

if hasattr(settings_module, 'ABOUT_PHOTO'):
    ABOUT_PHOTO = getattr(settings_module, 'ABOUT_PHOTO')
else:
    ABOUT_PHOTO = None

if hasattr(settings_module, 'FAVORITE_CHARACTERS'):
    FAVORITE_CHARACTERS = getattr(settings_module, 'FAVORITE_CHARACTERS')
    if hasattr(settings_module, 'FAVORITE_CHARACTER_TO_URL'):
        FAVORITE_CHARACTER_TO_URL = getattr(settings_module, 'FAVORITE_CHARACTER_TO_URL')
    else:
        FAVORITE_CHARACTER_TO_URL = lambda _: '#'
    if hasattr(settings_module, 'FAVORITE_CHARACTER_NAME'):
        FAVORITE_CHARACTER_NAME = getattr(settings_module, 'FAVORITE_CHARACTER_NAME')
    else:
        FAVORITE_CHARACTER_NAME = None
else:
    FAVORITE_CHARACTERS = None
    FAVORITE_CHARACTER_TO_URL = lambda _: '#'
    FAVORITE_CHARACTER_NAME = None

if hasattr(settings_module, 'DONATE_IMAGE'):
    DONATE_IMAGE = getattr(settings_module, 'DONATE_IMAGE')
else:
    DONATE_IMAGE = None

if hasattr(settings_module, 'DONATE_IMAGES_FOLDER'):
    DONATE_IMAGES_FOLDER = getattr(settings_module, 'DONATE_IMAGES_FOLDER')
else:
    DONATE_IMAGES_FOLDER = ''

if hasattr(settings_module, 'SITE_DESCRIPTION'):
    SITE_DESCRIPTION = getattr(settings_module, 'SITE_DESCRIPTION')
else:
    SITE_DESCRIPTION = _(u'The {game} Database & Community').format(game=GAME_NAME)

if hasattr(settings_module, 'ENABLED_NAVBAR_LISTS'):
    ENABLED_NAVBAR_LISTS = getattr(settings_module, 'ENABLED_NAVBAR_LISTS')
else:
    ENABLED_NAVBAR_LISTS = DEFAULT_ENABLED_NAVBAR_LISTS

if hasattr(settings_module, 'ENABLED_PAGES'):
    ENABLED_PAGES = getattr(settings_module, 'ENABLED_PAGES')
else:
    ENABLED_PAGES = DEFAULT_ENABLED_PAGES

if hasattr(settings_module, 'ENABLED_COLLECTIONS'):
    ENABLED_COLLECTIONS = getattr(settings_module, 'ENABLED_COLLECTIONS')
else:
    ENABLED_COLLECTIONS = DEFAULT_ENABLED_COLLECTIONS

if hasattr(settings_module, 'GET_GLOBAL_CONTEXT'):
    GET_GLOBAL_CONTEXT = getattr(settings_module, 'GET_GLOBAL_CONTEXT')
else:
    GET_GLOBAL_CONTEXT = None

if hasattr(settings_module, 'TWITTER_HANDLE'):
    TWITTER_HANDLE = getattr(settings_module, 'TWITTER_HANDLE')
else:
    TWITTER_HANDLE = None

if hasattr(settings_module, 'JAVASCRIPT_TRANSLATED_TERMS'):
    JAVASCRIPT_TRANSLATED_TERMS = getattr(settings_module, 'JAVASCRIPT_TRANSLATED_TERMS')
else:
    JAVASCRIPT_TRANSLATED_TERMS = DEFAULT_JAVASCRIPT_TRANSLATED_TERMS

if hasattr(settings_module, 'DONATORS_STATUS_CHOICES'):
    DONATORS_STATUS_CHOICES = getattr(settings_module, 'DONATORS_STATUS_CHOICES')
else:
    DONATORS_STATUS_CHOICES = None

if hasattr(settings_module, 'ACTIVITY_TAGS'):
    ACTIVITY_TAGS = getattr(settings_module, 'ACTIVITY_TAGS')
else:
    ACTIVITY_TAGS = None

if hasattr(settings_module, 'USER_COLORS'):
    USER_COLORS = getattr(settings_module, 'USER_COLORS')
else:
    USER_COLORS = None

if hasattr(settings_module, 'TRANSLATION_HELP_URL'):
    TRANSLATION_HELP_URL = getattr(settings_module, 'TRANSLATION_HELP_URL')
else:
    TRANSLATION_HELP_URL = 'https://poeditor.com/join/project/h6kGEpdnmM'

STATIC_UPLOADED_FILES_PREFIX = django_settings.STATIC_UPLOADED_FILES_PREFIX
