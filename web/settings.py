from django.conf import settings as django_settings
from web.default_settings import DEFAULT_ENABLED_NAVBAR_LISTS, DEFAULT_ENABLED_COLLECTIONS, DEFAULT_ENABLED_PAGES, RAW_CONTEXT, DEFAULT_JAVASCRIPT_TRANSLATED_TERMS, DEFAULT_PROFILE_EXTRA_TABS
from django.utils.translation import ugettext_lazy as _, string_concat

settings_module = __import__(django_settings.SITE + '.settings', globals(), locals(), ['*'])

############################################################
# Required settings

SITE_NAME = getattr(settings_module, 'SITE_NAME')
SITE_URL = getattr(settings_module, 'SITE_URL')
SITE_IMAGE = getattr(settings_module, 'SITE_IMAGE')
SITE_STATIC_URL = getattr(settings_module, 'SITE_STATIC_URL')
DISQUS_SHORTNAME = getattr(settings_module, 'DISQUS_SHORTNAME')
GAME_NAME = getattr(settings_module, 'GAME_NAME')
ACCOUNT_MODEL = getattr(settings_module, 'ACCOUNT_MODEL')
COLOR = getattr(settings_module, 'COLOR')

############################################################
# Optional settings with default values

if hasattr(settings_module, 'GITHUB_REPOSITORY'):
    GITHUB_REPOSITORY = getattr(settings_module, 'GITHUB_REPOSITORY')
else:
    GITHUB_REPOSITORY = ('SchoolIdolTomodachi', 'MagiCircles')

if hasattr(settings_module, 'WIKI'):
    WIKI = getattr(settings_module, 'WIKI')
else:
    WIKI = GITHUB_REPOSITORY

if hasattr(settings_module, 'EMAIL_IMAGE'):
    EMAIL_IMAGE = getattr(settings_module, 'EMAIL_IMAGE')
else:
    EMAIL_IMAGE = SITE_IMAGE

if hasattr(settings_module, 'BUG_TRACKER_URL'):
    BUG_TRACKER_URL = getattr(settings_module, 'BUG_TRACKER_URL')
else:
    BUG_TRACKER_URL = 'https://github.com/{}/{}/issues'.format(GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1])

if hasattr(settings_module, 'CONTRIBUTE_URL'):
    CONTRIBUTE_URL = getattr(settings_module, 'CONTRIBUTE_URL')
else:
    CONTRIBUTE_URL = 'https://github.com/SchoolIdolTomodachi/SchoolIdolAPI/wiki/Contribute'

if hasattr(settings_module, 'CALL_TO_ACTION'):
    CALL_TO_ACTION = getattr(settings_module, 'CALL_TO_ACTION')
else:
    CALL_TO_ACTION = _('Join the community!')

if hasattr(settings_module, 'CONTACT_EMAIL'):
    CONTACT_EMAIL = getattr(settings_module, 'CONTACT_EMAIL')
else:
    CONTACT_EMAIL = django_settings.AWS_SES_RETURN_PATH

if hasattr(settings_module, 'CONTACT_REDDIT'):
    CONTACT_REDDIT = getattr(settings_module, 'CONTACT_REDDIT')
else:
    CONTACT_REDDIT = 'db0company'

if hasattr(settings_module, 'CONTACT_FACEBOOK'):
    CONTACT_FACEBOOK = getattr(settings_module, 'CONTACT_FACEBOOK')
else:
    CONTACT_FACEBOOK = 'db0company'

if hasattr(settings_module, 'ABOUT_PHOTO'):
    ABOUT_PHOTO = getattr(settings_module, 'ABOUT_PHOTO')
else:
    ABOUT_PHOTO = 'engildeby.gif'

if hasattr(settings_module, 'SITE_DESCRIPTION'):
    SITE_DESCRIPTION = getattr(settings_module, 'SITE_DESCRIPTION')
else:
    SITE_DESCRIPTION = lambda: _(u'The {game} Database & Community').format(game=GAME_NAME)

if hasattr(settings_module, 'SITE_LONG_DESCRIPTION'):
    SITE_LONG_DESCRIPTION = getattr(settings_module, 'SITE_LONG_DESCRIPTION')
else:
    SITE_LONG_DESCRIPTION = lambda: _(u'{site} provides an extended database of information about the game {game} and allows you to keep track of your progress in the game. You can create and customize your very own profile to share your progress and your collection to all your friends. You can also meet other players like you with the social network: read what the others are doing and share your adventures with the community. Comment, like and follow the other players to grow your network. Find players near you with the global map of all the players. And much more!').format(site=SITE_NAME, game=GAME_NAME)

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

if hasattr(settings_module, 'TWITTER_HANDLE'):
    TWITTER_HANDLE = getattr(settings_module, 'TWITTER_HANDLE')
else:
    TWITTER_HANDLE = 'schoolidolu'

if hasattr(settings_module, 'TRANSLATION_HELP_URL'):
    TRANSLATION_HELP_URL = getattr(settings_module, 'TRANSLATION_HELP_URL')
else:
    TRANSLATION_HELP_URL = 'https://poeditor.com/join/project/h6kGEpdnmM'

if hasattr(settings_module, 'TOTAL_DONATORS'):
    TOTAL_DONATORS = getattr(settings_module, 'TOTAL_DONATORS')
else:
    TOTAL_DONATORS = 2

if hasattr(settings_module, 'EMPTY_IMAGE'):
    EMPTY_IMAGE = getattr(settings_module, 'EMPTY_IMAGE')
else:
    EMPTY_IMAGE = 'empty.png'

if hasattr(settings_module, 'SHOW_TOTAL_ACCOUNTS'):
    SHOW_TOTAL_ACCOUNTS = getattr(settings_module, 'SHOW_TOTAL_ACCOUNTS')
else:
    SHOW_TOTAL_ACCOUNTS = True

if hasattr(settings_module, 'GOOGLE_ANALYTICS'):
    GOOGLE_ANALYTICS = getattr(settings_module, 'GOOGLE_ANALYTICS')
else:
    GOOGLE_ANALYTICS = 'UA-67529921-1'

if hasattr(settings_module, 'STATIC_FILES_VERSION'):
    STATIC_FILES_VERSION = getattr(settings_module, 'STATIC_FILES_VERSION')
else:
    STATIC_FILES_VERSION = '1'

############################################################
# Optional settings without default values (= None)

if hasattr(settings_module, 'SITE_LOGO'):
    SITE_LOGO = getattr(settings_module, 'SITE_LOGO')
else:
    SITE_LOGO = None

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
if hasattr(settings_module, 'GET_GLOBAL_CONTEXT'):
    GET_GLOBAL_CONTEXT = getattr(settings_module, 'GET_GLOBAL_CONTEXT')
else:
    GET_GLOBAL_CONTEXT = None

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

if hasattr(settings_module, 'LATEST_NEWS'):
    LATEST_NEWS = getattr(settings_module, 'LATEST_NEWS')
else:
    LATEST_NEWS = None

if hasattr(settings_module, 'GAME_DESCRIPTION'):
    GAME_DESCRIPTION = getattr(settings_module, 'GAME_DESCRIPTION')
else:
    GAME_DESCRIPTION = None

if hasattr(settings_module, 'GAME_URL'):
    GAME_URL = getattr(settings_module, 'GAME_URL')
else:
    GAME_URL = None

if hasattr(settings_module, 'HASHTAGS'):
    HASHTAGS = getattr(settings_module, 'HASHTAGS')
else:
    HASHTAGS = []

if hasattr(settings_module, 'ON_USER_EDITED'):
    ON_USER_EDITED = getattr(settings_module, 'ON_USER_EDITED')
else:
    ON_USER_EDITED = None

if hasattr(settings_module, 'ON_PREFERENCES_EDITED'):
    ON_PREFERENCES_EDITED = getattr(settings_module, 'ON_PREFERENCES_EDITED')
else:
    ON_PREFERENCES_EDITED = None

if hasattr(settings_module, 'PROFILE_EXTRA_TABS'):
    PROFILE_EXTRA_TABS = getattr(settings_module, 'PROFILE_EXTRA_TABS')
else:
    PROFILE_EXTRA_TABS = DEFAULT_PROFILE_EXTRA_TABS

############################################################
# Specified in django settings

STATIC_UPLOADED_FILES_PREFIX = django_settings.STATIC_UPLOADED_FILES_PREFIX

############################################################
# Needed in django_settings

django_settings.SITE_URL = SITE_URL
django_settings.SITE_STATIC_URL = SITE_STATIC_URL
django_settings.GET_GLOBAL_CONTEXT = GET_GLOBAL_CONTEXT
