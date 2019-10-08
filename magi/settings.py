from django.conf import settings as django_settings
from magi.default_settings import (
    RAW_CONTEXT,
    DEFAULT_ENABLED_NAVBAR_LISTS,
    DEFAULT_ENABLED_PAGES,
    DEFAULT_JAVASCRIPT_TRANSLATED_TERMS,
    DEFAULT_PROFILE_TABS,
    DEFAULT_HOME_ACTIVITY_TABS,
    DEFAULT_PRELAUNCH_ENABLED_PAGES,
    DEFAULT_NAVBAR_ORDERING,
    DEFAULT_GROUPS,
    DEFAULT_GLOBAL_OUTSIDE_PERMISSIONS,
    DEFAULT_CONTACT_DISCORD,
    DEFAULT_LANGUAGES_CANT_SPEAK_ENGLISH,
    DEFAULT_EXTRA_PREFERENCES,
    DEFAULT_HOMEPAGE_ART_POSITION,
)
from magi.utils import globalContext, toHumanReadable
from django.utils.translation import ugettext_lazy as _, string_concat, get_language

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

# Required when COMMENTS_ENGINE = 'disqus' (default)
DISQUS_SHORTNAME = getattr(settings_module, 'DISQUS_SHORTNAME', None)

############################################################
# Optional settings with default values

if hasattr(settings_module, 'COMMENTS_ENGINE'):
    COMMENTS_ENGINE = getattr(settings_module, 'COMMENTS_ENGINE')
else:
    COMMENTS_ENGINE = 'disqus'

if hasattr(settings_module, 'SITE_LOGO'):
    SITE_LOGO = getattr(settings_module, 'SITE_LOGO')
else:
    SITE_LOGO = SITE_IMAGE

if hasattr(settings_module, 'GITHUB_REPOSITORY'):
    GITHUB_REPOSITORY = getattr(settings_module, 'GITHUB_REPOSITORY')
else:
    GITHUB_REPOSITORY = ('MagiCircles', 'MagiCircles')

if hasattr(settings_module, 'HELP_WIKI'):
    HELP_WIKI = getattr(settings_module, 'HELP_WIKI')
else:
    HELP_WIKI = ('MagiCircles', 'Circles')

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
    CONTRIBUTE_URL = '/help/Developers%20guide'

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

if hasattr(settings_module, 'CONTACT_DISCORD'):
    CONTACT_DISCORD = getattr(settings_module, 'CONTACT_DISCORD')
else:
    CONTACT_DISCORD = DEFAULT_CONTACT_DISCORD

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
    SITE_DESCRIPTION = lambda: _(u'The {game} Database & Community').format(
        game=GAME_NAME_PER_LANGUAGE.get(get_language(), GAME_NAME))

if hasattr(settings_module, 'SITE_LONG_DESCRIPTION'):
    SITE_LONG_DESCRIPTION = getattr(settings_module, 'SITE_LONG_DESCRIPTION')
else:
    SITE_LONG_DESCRIPTION = lambda: _(u'{site} provides an extended database of information about the game {game} and allows you to keep track of your progress in the game. You can create and customize your very own profile to share your progress and your collection to all your friends. You can also meet other players like you with the social network: read what the others are doing and share your adventures with the community. Comment, like and follow the other players to grow your network. Find players near you with the global map of all the players. And much more!').format(
        site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
        game=GAME_NAME_PER_LANGUAGE.get(get_language(), GAME_NAME))

if hasattr(settings_module, 'ENABLED_NAVBAR_LISTS'):
    ENABLED_NAVBAR_LISTS = getattr(settings_module, 'ENABLED_NAVBAR_LISTS')
else:
    ENABLED_NAVBAR_LISTS = DEFAULT_ENABLED_NAVBAR_LISTS

if hasattr(settings_module, 'NAVBAR_ORDERING'):
    NAVBAR_ORDERING = getattr(settings_module, 'NAVBAR_ORDERING')
else:
    NAVBAR_ORDERING = DEFAULT_NAVBAR_ORDERING

if hasattr(settings_module, 'ACCOUNT_TAB_ORDERING'):
    ACCOUNT_TAB_ORDERING = getattr(settings_module, 'ACCOUNT_TAB_ORDERING')
else:
    ACCOUNT_TAB_ORDERING = []

if hasattr(settings_module, 'ENABLED_PAGES'):
    ENABLED_PAGES = getattr(settings_module, 'ENABLED_PAGES')
else:
    ENABLED_PAGES = DEFAULT_ENABLED_PAGES

if hasattr(settings_module, 'TWITTER_HANDLE'):
    TWITTER_HANDLE = getattr(settings_module, 'TWITTER_HANDLE')
else:
    TWITTER_HANDLE = 'schoolidolu'

if hasattr(settings_module, 'TRANSLATION_HELP_URL'):
    TRANSLATION_HELP_URL = getattr(settings_module, 'TRANSLATION_HELP_URL')
else:
    TRANSLATION_HELP_URL = '/help/Translators%20guide'

if hasattr(settings_module, 'TOTAL_DONATORS'):
    TOTAL_DONATORS = getattr(settings_module, 'TOTAL_DONATORS')
else:
    TOTAL_DONATORS = 2

if hasattr(settings_module, 'MINIMUM_LIKES_POPULAR'):
    MINIMUM_LIKES_POPULAR = getattr(settings_module, 'MINIMUM_LIKES_POPULAR')
else:
    MINIMUM_LIKES_POPULAR = 10

if hasattr(settings_module, 'STAFF_CONFIGURATIONS'):
    STAFF_CONFIGURATIONS = getattr(settings_module, 'STAFF_CONFIGURATIONS')
else:
    STAFF_CONFIGURATIONS = {}

if hasattr(settings_module, 'EMPTY_IMAGE'):
    EMPTY_IMAGE = getattr(settings_module, 'EMPTY_IMAGE')
else:
    EMPTY_IMAGE = 'empty.png'

if hasattr(settings_module, 'SHOW_TOTAL_ACCOUNTS'):
    SHOW_TOTAL_ACCOUNTS = getattr(settings_module, 'SHOW_TOTAL_ACCOUNTS')
else:
    SHOW_TOTAL_ACCOUNTS = True

if hasattr(settings_module, 'ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT'):
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT = getattr(settings_module, 'ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT')
else:
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT = False

if hasattr(settings_module, 'LANGUAGES_CANT_SPEAK_ENGLISH'):
    LANGUAGES_CANT_SPEAK_ENGLISH = getattr(settings_module, 'LANGUAGES_CANT_SPEAK_ENGLISH')
else:
    LANGUAGES_CANT_SPEAK_ENGLISH = DEFAULT_LANGUAGES_CANT_SPEAK_ENGLISH

if hasattr(settings_module, 'ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES'):
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES = getattr(settings_module, 'ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES')
else:
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT_FOR_LANGUAGES = LANGUAGES_CANT_SPEAK_ENGLISH

if hasattr(settings_module, 'GOOGLE_ANALYTICS'):
    GOOGLE_ANALYTICS = getattr(settings_module, 'GOOGLE_ANALYTICS')
else:
    GOOGLE_ANALYTICS = 'UA-67529921-1'

if hasattr(settings_module, 'STATIC_FILES_VERSION'):
    STATIC_FILES_VERSION = getattr(settings_module, 'STATIC_FILES_VERSION')
else:
    STATIC_FILES_VERSION = '1'

if hasattr(settings_module, 'MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED'):
    MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED = getattr(settings_module, 'MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED')
else:
    MAX_LEVEL_BEFORE_SCREENSHOT_REQUIRED = 200

if hasattr(settings_module, 'MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED'):
    MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED = getattr(settings_module, 'MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED')
else:
    MAX_LEVEL_UP_STEP_BEFORE_SCREENSHOT_REQUIRED = 10

if hasattr(settings_module, 'PROFILE_TABS'):
    PROFILE_TABS = getattr(settings_module, 'PROFILE_TABS')
else:
    PROFILE_TABS = DEFAULT_PROFILE_TABS

if hasattr(settings_module, 'HOME_ACTIVITY_TABS'):
    HOME_ACTIVITY_TABS = getattr(settings_module, 'HOME_ACTIVITY_TABS')
else:
    HOME_ACTIVITY_TABS = DEFAULT_HOME_ACTIVITY_TABS

if hasattr(settings_module, 'MAX_ACTIVITY_HEIGHT'):
    MAX_ACTIVITY_HEIGHT = getattr(settings_module, 'MAX_ACTIVITY_HEIGHT')
else:
    MAX_ACTIVITY_HEIGHT = 1200

if hasattr(settings_module, 'PRELAUNCH_ENABLED_PAGES'):
    PRELAUNCH_ENABLED_PAGES = getattr(settings_module, 'PRELAUNCH_ENABLED_PAGES')
else:
    PRELAUNCH_ENABLED_PAGES = DEFAULT_PRELAUNCH_ENABLED_PAGES

if hasattr(settings_module, 'GROUPS'):
    GROUPS = getattr(settings_module, 'GROUPS')
else:
    GROUPS = DEFAULT_GROUPS

if hasattr(settings_module, 'GLOBAL_OUTSIDE_PERMISSIONS'):
    GLOBAL_OUTSIDE_PERMISSIONS = getattr(settings_module, 'GLOBAL_OUTSIDE_PERMISSIONS')
else:
    GLOBAL_OUTSIDE_PERMISSIONS = DEFAULT_GLOBAL_OUTSIDE_PERMISSIONS

if hasattr(settings_module, 'CUSTOM_PREFERENCES_FORM'):
    CUSTOM_PREFERENCES_FORM = getattr(settings_module, 'CUSTOM_PREFERENCES_FORM')
else:
    CUSTOM_PREFERENCES_FORM = False

if hasattr(settings_module, 'EXTRA_PREFERENCES'):
    EXTRA_PREFERENCES = getattr(settings_module, 'EXTRA_PREFERENCES')
else:
    EXTRA_PREFERENCES = DEFAULT_EXTRA_PREFERENCES

if hasattr(settings_module, 'HOMEPAGE_ART_POSITION'):
    HOMEPAGE_ART_POSITION = getattr(settings_module, 'HOMEPAGE_ART_POSITION')
else:
    HOMEPAGE_ART_POSITION = DEFAULT_HOMEPAGE_ART_POSITION

if hasattr(settings_module, 'HOMEPAGE_ART_SIDE'):
    HOMEPAGE_ART_SIDE = getattr(settings_module, 'HOMEPAGE_ART_SIDE')
else:
    HOMEPAGE_ART_SIDE = 'across'

if hasattr(settings_module, 'HOMEPAGE_ART_GRADIENT'):
    HOMEPAGE_ART_GRADIENT = getattr(settings_module, 'HOMEPAGE_ART_GRADIENT')
else:
    HOMEPAGE_ART_GRADIENT = False

if hasattr(settings_module, 'HOMEPAGE_RIBBON'):
    HOMEPAGE_RIBBON = getattr(settings_module, 'HOMEPAGE_RIBBON')
else:
    HOMEPAGE_RIBBON = False

if hasattr(settings_module, 'GOOD_REPUTATION_THRESHOLD'):
    GOOD_REPUTATION_THRESHOLD = getattr(settings_module, 'GOOD_REPUTATION_THRESHOLD')
else:
    GOOD_REPUTATION_THRESHOLD = 10

if hasattr(settings_module, 'CORNER_POPUP_IMAGE_OVERFLOW'):
    CORNER_POPUP_IMAGE_OVERFLOW = getattr(settings_module, 'CORNER_POPUP_IMAGE_OVERFLOW')
else:
    CORNER_POPUP_IMAGE_OVERFLOW = False

############################################################
# Optional settings without default values (= None)

if hasattr(settings_module, 'SITE_NAV_LOGO'):
    SITE_NAV_LOGO = getattr(settings_module, 'SITE_NAV_LOGO')
else:
    SITE_NAV_LOGO = None

if hasattr(settings_module, 'SITE_LOGO_PER_LANGUAGE'):
    SITE_LOGO_PER_LANGUAGE = getattr(settings_module, 'SITE_LOGO_PER_LANGUAGE')
else:
    SITE_LOGO_PER_LANGUAGE = None

if hasattr(settings_module, 'SITE_IMAGE_PER_LANGUAGE'):
    SITE_IMAGE_PER_LANGUAGE = getattr(settings_module, 'SITE_IMAGE_PER_LANGUAGE')
else:
    SITE_IMAGE_PER_LANGUAGE = {}

if hasattr(settings_module, 'EMAIL_IMAGE_PER_LANGUAGE'):
    EMAIL_IMAGE_PER_LANGUAGE = getattr(settings_module, 'EMAIL_IMAGE_PER_LANGUAGE')
else:
    EMAIL_IMAGE_PER_LANGUAGE = {}

if hasattr(settings_module, 'SITE_NAME_PER_LANGUAGE'):
    SITE_NAME_PER_LANGUAGE = getattr(settings_module, 'SITE_NAME_PER_LANGUAGE')
else:
    SITE_NAME_PER_LANGUAGE = {}

if hasattr(settings_module, 'GAME_NAME_PER_LANGUAGE'):
    GAME_NAME_PER_LANGUAGE = getattr(settings_module, 'GAME_NAME_PER_LANGUAGE')
else:
    GAME_NAME_PER_LANGUAGE = {}

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

if hasattr(settings_module, 'BACKGROUNDS'):
    BACKGROUNDS = getattr(settings_module, 'BACKGROUNDS')
else:
    BACKGROUNDS = None

if hasattr(django_settings, 'STAFF_CONFIGURATIONS') and 'donate_image' in django_settings.STAFF_CONFIGURATIONS:
    DONATE_IMAGE = django_settings.STAFF_CONFIGURATIONS['donate_image']
elif hasattr(settings_module, 'DONATE_IMAGE'):
    DONATE_IMAGE = getattr(settings_module, 'DONATE_IMAGE')
else:
    DONATE_IMAGE = None

if hasattr(settings_module, 'LAUNCH_DATE'):
    LAUNCH_DATE = getattr(settings_module, 'LAUNCH_DATE')
else:
    LAUNCH_DATE = None

if hasattr(settings_module, 'REDIRECT_AFTER_SIGNUP'):
    REDIRECT_AFTER_SIGNUP = getattr(settings_module, 'REDIRECT_AFTER_SIGNUP')
else:
    REDIRECT_AFTER_SIGNUP = None

if hasattr(settings_module, 'GET_GLOBAL_CONTEXT'):
    GET_GLOBAL_CONTEXT = getattr(settings_module, 'GET_GLOBAL_CONTEXT')
else:
    GET_GLOBAL_CONTEXT = globalContext

if hasattr(settings_module, 'JAVASCRIPT_TRANSLATED_TERMS'):
    JAVASCRIPT_TRANSLATED_TERMS = getattr(settings_module, 'JAVASCRIPT_TRANSLATED_TERMS')
else:
    JAVASCRIPT_TRANSLATED_TERMS = DEFAULT_JAVASCRIPT_TRANSLATED_TERMS

if hasattr(settings_module, 'DONATORS_STATUS_CHOICES'):
    DONATORS_STATUS_CHOICES = getattr(settings_module, 'DONATORS_STATUS_CHOICES')
else:
    DONATORS_STATUS_CHOICES = None

if hasattr(django_settings, 'STAFF_CONFIGURATIONS') and 'donators_goal' in django_settings.STAFF_CONFIGURATIONS:
    try:
        DONATORS_GOAL = int(django_settings.STAFF_CONFIGURATIONS['donators_goal'])
    except ValueError:
        DONATORS_GOAL = None
elif hasattr(settings_module, 'DONATORS_GOAL'):
    DONATORS_GOAL = getattr(settings_module, 'DONATORS_GOAL')
else:
    DONATORS_GOAL = None

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

if hasattr(settings_module, 'FEEDBACK_FORM'):
    FEEDBACK_FORM = getattr(settings_module, 'FEEDBACK_FORM')
else:
    FEEDBACK_FORM = None

if hasattr(settings_module, 'HASHTAGS'):
    HASHTAGS = getattr(settings_module, 'HASHTAGS')
else:
    HASHTAGS = []

if hasattr(settings_module, 'FIRST_COLLECTION'):
    FIRST_COLLECTION = getattr(settings_module, 'FIRST_COLLECTION')
else:
    FIRST_COLLECTION = None

if hasattr(settings_module, 'GET_STARTED_VIDEO'):
    GET_STARTED_VIDEO = getattr(settings_module, 'GET_STARTED_VIDEO')
else:
    GET_STARTED_VIDEO = None

if hasattr(settings_module, 'ON_USER_EDITED'):
    ON_USER_EDITED = getattr(settings_module, 'ON_USER_EDITED')
else:
    ON_USER_EDITED = None

if hasattr(settings_module, 'ON_PREFERENCES_EDITED'):
    ON_PREFERENCES_EDITED = getattr(settings_module, 'ON_PREFERENCES_EDITED')
else:
    ON_PREFERENCES_EDITED = None

if hasattr(settings_module, 'CORNER_POPUP_IMAGE'):
    CORNER_POPUP_IMAGE = getattr(settings_module, 'CORNER_POPUP_IMAGE')
else:
    CORNER_POPUP_IMAGE = None

if hasattr(settings_module, 'HOMEPAGE_BACKGROUND'):
    HOMEPAGE_BACKGROUND = getattr(settings_module, 'HOMEPAGE_BACKGROUND')
else:
    HOMEPAGE_BACKGROUND = None

if hasattr(settings_module, 'HOMEPAGE_ARTS'):
    HOMEPAGE_ARTS = getattr(settings_module, 'HOMEPAGE_ARTS')
else:
    HOMEPAGE_ARTS = None

if hasattr(settings_module, 'RANDOM_ART_FOR_CHARACTER'):
    RANDOM_ART_FOR_CHARACTER = getattr(settings_module, 'RANDOM_ART_FOR_CHARACTER')
else:
    RANDOM_ART_FOR_CHARACTER = None

if hasattr(settings_module, 'JAVASCRIPT_COMMONS'):
    JAVASCRIPT_COMMONS = getattr(settings_module, 'JAVASCRIPT_COMMONS')
else:
    JAVASCRIPT_COMMONS = None

if hasattr(settings_module, 'USERS_REPUTATION_CALCULATOR'):
    USERS_REPUTATION_CALCULATOR = getattr(settings_module, 'USERS_REPUTATION_CALCULATOR')
else:
    USERS_REPUTATION_CALCULATOR = None

############################################################
# Specified in django settings

STATIC_UPLOADED_FILES_PREFIX = django_settings.STATIC_UPLOADED_FILES_PREFIX

############################################################
# Needed in django_settings

django_settings.SITE_URL = SITE_URL
django_settings.SITE_STATIC_URL = SITE_STATIC_URL
django_settings.GET_GLOBAL_CONTEXT = GET_GLOBAL_CONTEXT

############################################################
# Post processing of settings

# Art position defaults

for _k, _v in DEFAULT_HOMEPAGE_ART_POSITION.items():
    if _k not in HOMEPAGE_ART_POSITION:
        HOMEPAGE_ART_POSITION[_k] = _v

# Permissions

def _set_permission_link_on_unset(d, permission, url):
    if url and permission in d and not d[permission]:
        d[permission] = url

# GROUPS

_permission_url_to_set = {
    'team': {
        'Administrate the contributors on GitHub': {
            'image': 'links/github',
            'url': u'https://github.com/{}/{}/settings/collaboration'.format(
                GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1]),
        },
        'Administrate the moderators on Disqus': {
            'icon': 'comments',
            'url': u'https://{}.disqus.com/admin/settings/moderators/'.format(DISQUS_SHORTNAME),
        },
    },
    'support': {
        'Receive private messages on Facebook': {
            'image': 'links/facebook',
            'url': u'https://facebook.com/{}/'.format(CONTACT_FACEBOOK) if CONTACT_FACEBOOK else None,
        },
        'Receive private messages on Reddit': {
            'image': 'links/reddit',
            'url': u'https://www.reddit.com/user/{}/'.format(CONTACT_REDDIT) if CONTACT_REDDIT else None,
        },
    },
    'd_moderator': {
        'Disqus moderation': {
            'icon': 'comments',
            'url': u'https://{}.disqus.com/admin/moderate/#/pending'.format(DISQUS_SHORTNAME),
        },
    },
    'manager': {
        'Disqus moderation': {
            'icon': 'comments',
            'url': u'https://{}.disqus.com/admin/moderate/#/pending'.format(DISQUS_SHORTNAME),
        },
    },
}

for _g, _d in GROUPS:
    _d['name'] = _g
    # Add missing outside permission urls based on settings
    if 'outside_permissions' in _d:
        for _p, _u in _permission_url_to_set.get(_g, {}).items():
            _set_permission_link_on_unset(_d['outside_permissions'], _p, _u)
    if _g == 'support' and FEEDBACK_FORM:
        if 'outside_permissions' not in _d:
            _d['outside_permissions'] = {}
        _d['outside_permissions']['Feedback form'] = { 'icon': 'idea', 'url': FEEDBACK_FORM }
    # Add staff details edit permission
    if _d.get('requires_staff', False):
        if 'permissions' not in _d:
            _d['permissions'] = []
        _d['permissions'].append('edit_own_staff_profile')
    # Add verbose_permissions
    if 'permissions' in _d:
        _d['verbose_permissions'] = [toHumanReadable(_p) for _p in _d['permissions']]

# GLOBAL_OUTSIDE_PERMISSIONS

for _permission, _url in [
        ('Bug tracker', { 'icon': 'bug', 'url': BUG_TRACKER_URL }),
]:
    _set_permission_link_on_unset(GLOBAL_OUTSIDE_PERMISSIONS, _permission, _url)

if WIKI:
    GLOBAL_OUTSIDE_PERMISSIONS['Wiki editor'] = {
        'icon': 'wiki',
        'url': 'https://github.com/{}/{}/wiki'.format(WIKI[0], WIKI[1]),
    }

# Enabled pages defaults

def _set_default_for_page(page_name, setting, value):
    if page_name in ENABLED_PAGES:
        for page in (
                ENABLED_PAGES[page_name]
                if isinstance(ENABLED_PAGES[page_name], list)
                else [ENABLED_PAGES[page_name]]):
            if setting not in page:
                page[setting] = value

_wiki_page_description = lambda: u'{} - {}'.format(
    _('Help'), _('Learn a few tips and tricks to help you easily use {site}.'.format(
        site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME))))

for _args in [
        ('about', 'page_description', SITE_LONG_DESCRIPTION),
        ('about_game', 'page_description', GAME_DESCRIPTION),
        ('map', 'page_description', lambda: _('Map of all {license} fans around the world.').format(
            license=GAME_NAME_PER_LANGUAGE.get(get_language(), GAME_NAME))),
        ('help', 'page_description', _wiki_page_description),
        ('wiki', 'page_description', _wiki_page_description),
]:
    _set_default_for_page(*_args)

# Sitemap pages for navbar

for _navbar_link_name, _navbar_link in ENABLED_NAVBAR_LISTS.items():
    if _navbar_link_name not in ENABLED_PAGES:
        ENABLED_PAGES[_navbar_link_name] = {
            'custom': False,
            'title': _navbar_link['title'],
            'icon': _navbar_link.get('icon', None),
            'image': _navbar_link.get('image', None),
            'navbar_link': False,
            'template': 'sitemap',
            'function_name': 'sitemap',
        }
        if not ENABLED_PAGES[_navbar_link_name]['icon'] and not ENABLED_PAGES[_navbar_link_name]['image']:
            ENABLED_PAGES[_navbar_link_name]['icon'] = 'category'
