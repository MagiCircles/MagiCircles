import datetime
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django.conf import settings as django_settings
from django.utils import timezone
from magi.default_settings import (
    RAW_CONTEXT,
    DEFAULT_ACTIVITY_TAGS,
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
    DEFAULT_SEASONS,
    DEFAULT_USER_COLORS,
)
from magi.utils import (
    complementaryColor,
    globalContext,
    toHumanReadable,
    getMagiCollection,
    getEventStatus,
    tourldash,
    failSafe,
)
from django.utils.translation import ugettext_lazy as _, string_concat, get_language

settings_module = __import__(django_settings.SITE + '.settings', globals(), locals(), ['*'])

############################################################
# Required settings

SITE_NAME = getattr(settings_module, 'SITE_NAME')
SITE_URL = (
    u'http://localhost:{}/'.format(django_settings.DEBUG_PORT)
    if django_settings.DEBUG
    else getattr(settings_module, 'SITE_URL')
)
SITE_IMAGE = getattr(settings_module, 'SITE_IMAGE')
SITE_STATIC_URL = (
    u'http://localhost:{}/'.format(django_settings.DEBUG_PORT)
    if django_settings.DEBUG
    else getattr(settings_module, 'SITE_STATIC_URL')
)
GAME_NAME = getattr(settings_module, 'GAME_NAME')
ACCOUNT_MODEL = getattr(settings_module, 'ACCOUNT_MODEL')
COLOR = getattr(settings_module, 'COLOR')

# Required when COMMENTS_ENGINE = 'disqus' (default)
DISQUS_SHORTNAME = getattr(settings_module, 'DISQUS_SHORTNAME', None)

############################################################
# Optional settings with default values

if hasattr(settings_module, 'SECONDARY_COLOR'):
    SECONDARY_COLOR = getattr(settings_module, 'SECONDARY_COLOR')
else:
    SECONDARY_COLOR = complementaryColor(hex_color=COLOR) if COLOR else None

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

if hasattr(settings_module, 'SEASONS'):
    SEASONS = getattr(settings_module, 'SEASONS')
else:
    SEASONS = DEFAULT_SEASONS

if hasattr(settings_module, 'TRANSLATION_HELP_URL'):
    TRANSLATION_HELP_URL = getattr(settings_module, 'TRANSLATION_HELP_URL')
else:
    TRANSLATION_HELP_URL = '/help/Translators%20guide'

if hasattr(django_settings, 'TOTAL_DONATORS'):
    TOTAL_DONATORS = getattr(django_settings, 'TOTAL_DONATORS')
elif hasattr(settings_module, 'TOTAL_DONATORS'):
    TOTAL_DONATORS = getattr(settings_module, 'TOTAL_DONATORS')
else:
    TOTAL_DONATORS = 2

if hasattr(settings_module, 'MINIMUM_LIKES_POPULAR'):
    MINIMUM_LIKES_POPULAR = getattr(settings_module, 'MINIMUM_LIKES_POPULAR')
else:
    MINIMUM_LIKES_POPULAR = 10

if hasattr(django_settings, 'STAFF_CONFIGURATIONS'):
    STAFF_CONFIGURATIONS = getattr(django_settings, 'STAFF_CONFIGURATIONS')
elif hasattr(settings_module, 'STAFF_CONFIGURATIONS'):
    STAFF_CONFIGURATIONS = getattr(settings_module, 'STAFF_CONFIGURATIONS')
else:
    STAFF_CONFIGURATIONS = {}

if hasattr(settings_module, 'EMPTY_IMAGE'):
    EMPTY_IMAGE = getattr(settings_module, 'EMPTY_IMAGE')
else:
    EMPTY_IMAGE = 'empty.png'

if hasattr(settings_module, 'ACTIVITY_TAGS'):
    ACTIVITY_TAGS = getattr(settings_module, 'ACTIVITY_TAGS')
else:
    ACTIVITY_TAGS = DEFAULT_ACTIVITY_TAGS

if hasattr(django_settings, 'ACTIVITY_TAGS'):
    ACTIVITY_TAGS += getattr(django_settings, 'ACTIVITY_TAGS')

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

if hasattr(settings_module, 'GOOGLE_ANALYTICS_GA4'):
    GOOGLE_ANALYTICS_GA4 = getattr(settings_module, 'GOOGLE_ANALYTICS_GA4')
else:
    GOOGLE_ANALYTICS_GA4 = None

if hasattr(settings_module, 'GOOGLE_ANALYTICS'):
    GOOGLE_ANALYTICS = getattr(settings_module, 'GOOGLE_ANALYTICS')
else:
    GOOGLE_ANALYTICS = 'UA-67529921-1'

if hasattr(django_settings, 'STATIC_FILES_VERSION'):
    STATIC_FILES_VERSION = getattr(django_settings, 'STATIC_FILES_VERSION')
elif hasattr(settings_module, 'STATIC_FILES_VERSION'):
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

if hasattr(settings_module, 'USER_COLORS'):
    USER_COLORS = getattr(settings_module, 'USER_COLORS')
else:
    USER_COLORS = DEFAULT_USER_COLORS

############################################################
# Optional settings without default values (= None)

if hasattr(settings_module, 'TWITTER_HANDLE'):
    TWITTER_HANDLE = getattr(settings_module, 'TWITTER_HANDLE')
else:
    TWITTER_HANDLE = None

if hasattr(settings_module, 'INSTAGRAM_HANDLE'):
    INSTAGRAM_HANDLE = getattr(settings_module, 'INSTAGRAM_HANDLE')
else:
    INSTAGRAM_HANDLE = None

if hasattr(settings_module, 'FACEBOOK_HANDLE'):
    FACEBOOK_HANDLE = getattr(settings_module, 'FACEBOOK_HANDLE')
else:
    FACEBOOK_HANDLE = None

if hasattr(settings_module, 'CONTACT_FACEBOOK'):
    CONTACT_FACEBOOK = getattr(settings_module, 'CONTACT_FACEBOOK')
else:
    CONTACT_FACEBOOK = FACEBOOK_HANDLE or 'db0company'

if hasattr(settings_module, 'COMMUNITY_DISCORD'):
    COMMUNITY_DISCORD = getattr(settings_module, 'COMMUNITY_DISCORD')
else:
    COMMUNITY_DISCORD = None

if hasattr(settings_module, 'SITE_LOGO_WHEN_LOGGED_IN'):
    SITE_LOGO_WHEN_LOGGED_IN = getattr(settings_module, 'SITE_LOGO_WHEN_LOGGED_IN')
else:
    SITE_LOGO_WHEN_LOGGED_IN = None

if hasattr(settings_module, 'ACCENT_COLOR'):
    ACCENT_COLOR = getattr(settings_module, 'ACCENT_COLOR')
else:
    ACCENT_COLOR = None

if hasattr(settings_module, 'SITE_NAV_LOGO'):
    SITE_NAV_LOGO = getattr(settings_module, 'SITE_NAV_LOGO')
else:
    SITE_NAV_LOGO = None

if hasattr(settings_module, 'SITE_LOGO_PER_LANGUAGE'):
    SITE_LOGO_PER_LANGUAGE = getattr(settings_module, 'SITE_LOGO_PER_LANGUAGE')
else:
    SITE_LOGO_PER_LANGUAGE = None

if hasattr(settings_module, 'SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE'):
    SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE = getattr(settings_module, 'SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE')
else:
    SITE_LOGO_WHEN_LOGGED_IN_PER_LANGUAGE = None

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

if hasattr(settings_module, 'SITE_EMOJIS'):
    SITE_EMOJIS = getattr(settings_module, 'SITE_EMOJIS')
else:
    SITE_EMOJIS = None

if hasattr(settings_module, 'MANY_CHARACTERS_THRESHOLD'):
    MANY_CHARACTERS_THRESHOLD = getattr(settings_module, 'MANY_CHARACTERS_THRESHOLD')
else:
    MANY_CHARACTERS_THRESHOLD = 30

if hasattr(django_settings, 'FAVORITE_CHARACTERS'):
    FAVORITE_CHARACTERS = getattr(django_settings, 'FAVORITE_CHARACTERS')
else:
    FAVORITE_CHARACTERS = None

if hasattr(settings_module, 'FAVORITE_CHARACTERS_MODEL'):  # Used by generated settings
    FAVORITE_CHARACTERS_MODEL = getattr(settings_module, 'FAVORITE_CHARACTERS_MODEL')
    FAVORITE_CHARACTERS_FILTER = getattr(settings_module, 'FAVORITE_CHARACTERS_FILTER', lambda _q: _q)
    FAVORITE_CHARACTER_TO_URL = lambda _link: u'/{}/{}/{}/'.format(
        FAVORITE_CHARACTERS_MODEL.collection_name,
        _link.raw_value,
        tourldash(_link.value),
    )
    FAVORITE_CHARACTER_NAME = lambda: (
        failSafe(lambda: getMagiCollection(
            FAVORITE_CHARACTERS_MODEL.collection_name).title, exceptions=[ AttributeError ])
        or failSafe(lambda: toHumanReadable(
            FAVORITE_CHARACTERS_MODEL.__class__.__name__, warning=True), exceptions=[ AttributeError ])
    )
    if hasattr(settings_module, 'HAS_MANY_FAVORITE_CHARACTERS'):
        HAS_MANY_FAVORITE_CHARACTERS = getattr(settings_module, 'HAS_MANY_FAVORITE_CHARACTERS')
    elif hasattr(django_settings, 'HAS_MANY_FAVORITE_CHARACTERS'):
        HAS_MANY_FAVORITE_CHARACTERS = getattr(django_settings, 'HAS_MANY_FAVORITE_CHARACTERS')
    else:
        HAS_MANY_FAVORITE_CHARACTERS = False
else:
    FAVORITE_CHARACTERS_MODEL = None
    FAVORITE_CHARACTERS_FILTER = lambda _q: _q
    FAVORITE_CHARACTER_TO_URL = lambda _: '#'
    FAVORITE_CHARACTER_NAME = None
    HAS_MANY_FAVORITE_CHARACTERS = False

if hasattr(settings_module, 'FAVORITE_CHARACTER_TO_URL'):
    FAVORITE_CHARACTER_TO_URL = getattr(settings_module, 'FAVORITE_CHARACTER_TO_URL')
if hasattr(settings_module, 'FAVORITE_CHARACTER_NAME'):
    FAVORITE_CHARACTER_NAME = getattr(settings_module, 'FAVORITE_CHARACTER_NAME')

if hasattr(settings_module, 'BACKGROUNDS_MODEL'): # Used by generated settings
    BACKGROUNDS_MODEL = getattr(settings_module, 'BACKGROUNDS_MODEL')
    BACKGROUNDS_FILTER = getattr(settings_module, 'BACKGROUNDS_FILTER', lambda _q: _q)
    if hasattr(settings_module, 'HAS_MANY_BACKGROUNDS'):
        HAS_MANY_BACKGROUNDS = getattr(settings_module, 'HAS_MANY_BACKGROUNDS')
    elif hasattr(django_settings, 'HAS_MANY_BACKGROUNDS'):
        HAS_MANY_BACKGROUNDS = getattr(django_settings, 'HAS_MANY_BACKGROUNDS')
    else:
        HAS_MANY_BACKGROUNDS = False
else:
    BACKGROUNDS_MODEL = None
    BACKGROUNDS_FILTER = lambda _q: _q
    HAS_MANY_BACKGROUNDS = False

if hasattr(django_settings, 'BACKGROUNDS'):
    BACKGROUNDS = getattr(django_settings, 'BACKGROUNDS')
elif hasattr(settings_module, 'BACKGROUNDS'):
    BACKGROUNDS = getattr(settings_module, 'BACKGROUNDS')
else:
    BACKGROUNDS = None

if hasattr(settings_module, 'SHOW_BACKGROUND_NAME_ON_SELECTION'):
    SHOW_BACKGROUND_NAME_ON_SELECTION = getattr(settings_module, 'SHOW_BACKGROUND_NAME_ON_SELECTION')
else:
    SHOW_BACKGROUND_NAME_ON_SELECTION = True

if hasattr(settings_module, 'MANY_BACKGROUNDS_THRESHOLD'):
    MANY_BACKGROUNDS_THRESHOLD = getattr(settings_module, 'MANY_BACKGROUNDS_THRESHOLD')
else:
    MANY_BACKGROUNDS_THRESHOLD = 30

if hasattr(django_settings, 'HOMEPAGE_BACKGROUNDS'):
    HOMEPAGE_BACKGROUNDS = getattr(django_settings, 'HOMEPAGE_BACKGROUNDS')
elif hasattr(settings_module, 'HOMEPAGE_BACKGROUNDS'):
    HOMEPAGE_BACKGROUNDS = getattr(settings_module, 'HOMEPAGE_BACKGROUNDS')
else:
    HOMEPAGE_BACKGROUNDS = []

if hasattr(django_settings, 'PROFILE_BACKGROUNDS'):
    PROFILE_BACKGROUNDS = getattr(django_settings, 'PROFILE_BACKGROUNDS')
elif hasattr(settings_module, 'PROFILE_BACKGROUNDS'):
    PROFILE_BACKGROUNDS = getattr(settings_module, 'PROFILE_BACKGROUNDS')
else:
    PROFILE_BACKGROUNDS = []

if BACKGROUNDS and not HOMEPAGE_BACKGROUNDS:
    HOMEPAGE_BACKGROUNDS = [
        _background
        for _background in BACKGROUNDS
        if _background.get('homepage', True)
    ]

if BACKGROUNDS and not PROFILE_BACKGROUNDS:
    PROFILE_BACKGROUNDS = [
        _background
        for _background in BACKGROUNDS
        if _background.get('profile', True)
    ]

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

if hasattr(settings_module, 'BETA_TEST_IN_PROGRESS'):
    BETA_TEST_IN_PROGRESS = getattr(settings_module, 'BETA_TEST_IN_PROGRESS')
else:
    BETA_TEST_IN_PROGRESS = False

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

if hasattr(django_settings, 'LATEST_NEWS'):
    LATEST_NEWS = getattr(django_settings, 'LATEST_NEWS')
elif hasattr(settings_module, 'LATEST_NEWS'):
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

if hasattr(settings_module, 'FEEDBACK_FORM_ANSWERS'):
    FEEDBACK_FORM_ANSWERS = getattr(settings_module, 'FEEDBACK_FORM_ANSWERS')
else:
    FEEDBACK_FORM_ANSWERS = FEEDBACK_FORM

if hasattr(settings_module, 'EVENT_FEEDBACK_FORM'):
    EVENT_FEEDBACK_FORM = getattr(settings_module, 'EVENT_FEEDBACK_FORM')
else:
    EVENT_FEEDBACK_FORM = None

if hasattr(settings_module, 'EVENT_FEEDBACK_FORM_ANSWERS'):
    EVENT_FEEDBACK_FORM_ANSWERS = getattr(settings_module, 'EVENT_FEEDBACK_FORM_ANSWERS')
else:
    EVENT_FEEDBACK_FORM_ANSWERS = EVENT_FEEDBACK_FORM

if hasattr(settings_module, 'EVENT_PRIZES_FORM'):
    EVENT_PRIZES_FORM = getattr(settings_module, 'EVENT_PRIZES_FORM')
else:
    EVENT_PRIZES_FORM = None

if hasattr(settings_module, 'EVENT_PRIZES_FORM_ANSWERS'):
    EVENT_PRIZES_FORM_ANSWERS = getattr(settings_module, 'EVENT_PRIZES_FORM_ANSWERS')
else:
    EVENT_PRIZES_FORM_ANSWERS = EVENT_PRIZES_FORM

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

if hasattr(settings_module, 'GET_STARTED_MARKDOWN_TUTORIAL'):
    GET_STARTED_MARKDOWN_TUTORIAL = getattr(settings_module, 'GET_STARTED_MARKDOWN_TUTORIAL')
else:
    GET_STARTED_MARKDOWN_TUTORIAL = None

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

if hasattr(django_settings, 'HOMEPAGE_ARTS'):
    HOMEPAGE_ARTS = getattr(django_settings, 'HOMEPAGE_ARTS')
else:
    HOMEPAGE_ARTS = []

if hasattr(settings_module, 'HOMEPAGE_ARTS'):
    HOMEPAGE_ARTS += getattr(settings_module, 'HOMEPAGE_ARTS')

if hasattr(settings_module, 'RANDOM_ART_FOR_CHARACTER'):
    RANDOM_ART_FOR_CHARACTER = getattr(settings_module, 'RANDOM_ART_FOR_CHARACTER')
else:
    RANDOM_ART_FOR_CHARACTER = None

if hasattr(settings_module, 'RANDOM_ART_FOR_CHARACTER_BIRTHDAY'):
    RANDOM_ART_FOR_CHARACTER_BIRTHDAY = getattr(settings_module, 'RANDOM_ART_FOR_CHARACTER_BIRTHDAY')
else:
    RANDOM_ART_FOR_CHARACTER_BIRTHDAY = None

if hasattr(settings_module, 'JAVASCRIPT_COMMONS'):
    JAVASCRIPT_COMMONS = getattr(settings_module, 'JAVASCRIPT_COMMONS')
else:
    JAVASCRIPT_COMMONS = None

if hasattr(settings_module, 'USERS_REPUTATION_CALCULATOR'):
    USERS_REPUTATION_CALCULATOR = getattr(settings_module, 'USERS_REPUTATION_CALCULATOR')
else:
    USERS_REPUTATION_CALCULATOR = None

if hasattr(settings_module, 'MAX_LEVEL'):
    MAX_LEVEL = getattr(settings_module, 'MAX_LEVEL')
else:
    MAX_LEVEL = None

if hasattr(settings_module, 'BIRTHDAY_TAG'):
    BIRTHDAY_TAG = getattr(settings_module, 'BIRTHDAY_TAG')
else:
    BIRTHDAY_TAG = None

if hasattr(settings_module, 'BIRTHDAY_BANNER_HIDE_TITLE'):
    BIRTHDAY_BANNER_HIDE_TITLE = getattr(settings_module, 'BIRTHDAY_BANNER_HIDE_TITLE')
else:
    BIRTHDAY_BANNER_HIDE_TITLE = False

if hasattr(settings_module, 'USERS_BIRTHDAYS_BANNER'):
    USERS_BIRTHDAYS_BANNER = getattr(settings_module, 'USERS_BIRTHDAYS_BANNER')
else:
    USERS_BIRTHDAYS_BANNER = None

############################################################
# Used by generated settings only

if hasattr(settings_module, 'GET_HOMEPAGE_ARTS'):
    GET_HOMEPAGE_ARTS = getattr(settings_module, 'GET_HOMEPAGE_ARTS')
else:
    GET_HOMEPAGE_ARTS = None

if hasattr(settings_module, 'GET_BACKGROUNDS'):
    GET_BACKGROUNDS = getattr(settings_module, 'GET_BACKGROUNDS')
else:
    GET_BACKGROUNDS = None

if hasattr(settings_module, 'OTHER_CHARACTERS_MODELS'):
    OTHER_CHARACTERS_MODELS = getattr(settings_module, 'OTHER_CHARACTERS_MODELS')
else:
    OTHER_CHARACTERS_MODELS = {}
    # Dict of cache variable name ("VOICE_ACTRESSES") -> Dict of {
    #     model, filter, allow_set_as_favorite_on_profile, how_many_favorites, has_many, many_threshold,
    # }

############################################################
# Specified in django settings

STATIC_UPLOADED_FILES_PREFIX = django_settings.STATIC_UPLOADED_FILES_PREFIX

############################################################
# Needed in django_settings

django_settings.SITE_URL = SITE_URL
django_settings.SITE_STATIC_URL = SITE_STATIC_URL
django_settings.GET_GLOBAL_CONTEXT = GET_GLOBAL_CONTEXT

############################################################
# Utils

LAST_SERVER_RESTART = timezone.now()

# For backgrounds

def _toBackgroundNameLambda(_b):
    return lambda: _b.get('d_names', {}).get(get_language(), _b.get('name', None))

HOMEPAGE_BACKGROUNDS_IMAGES = OrderedDict([
    (_b['id'], _b['image'])
    for _b in HOMEPAGE_BACKGROUNDS or []
])
HOMEPAGE_BACKGROUNDS_THUMBNAILS = OrderedDict([
    (_b['id'], _b.get('thumbnail', _b['image']))
    for _b in HOMEPAGE_BACKGROUNDS or []
])
HOMEPAGE_BACKGROUNDS_NAMES = OrderedDict([
    (_b['id'], _toBackgroundNameLambda(_b))
    for _b in HOMEPAGE_BACKGROUNDS or []
])

PROFILE_BACKGROUNDS_IMAGES = OrderedDict([
    (_b['id'], _b['image'])
    for _b in PROFILE_BACKGROUNDS or []
])
PROFILE_BACKGROUNDS_THUMBNAILS = OrderedDict([
    (_b['id'], _b.get('thumbnail', _b['image']))
    for _b in PROFILE_BACKGROUNDS or []
])
PROFILE_BACKGROUNDS_NAMES = OrderedDict([
    (_b['id'], _toBackgroundNameLambda(_b))
    for _b in PROFILE_BACKGROUNDS or []
])

# For characters

############################################################
# Post processing of settings

# Extra preferences from other characters model

_extra_extra_preferences = []
for _key, _details in OTHER_CHARACTERS_MODELS.items():
    _model = _details['model'] if isinstance(_details, dict) else _details
    _total = (_details.get('how_many_favorites', None) if isinstance(_details, dict) else None) or 1
    if _total > 1:
        for _nth in range(1, _total + 1):
            _extra_extra_preferences.append(u'favorite_{}{}'.format(_model.collection_name, _nth))
    else:
        _extra_extra_preferences.append(u'favorite_{}'.format(_model.collection_name))

EXTRA_PREFERENCES = _extra_extra_preferences + EXTRA_PREFERENCES

# Art position defaults

for _k, _v in DEFAULT_HOMEPAGE_ART_POSITION.items():
    if _k not in HOMEPAGE_ART_POSITION:
        HOMEPAGE_ART_POSITION[_k] = _v

# Add characters birthdays to activity tags

_CHARACTERS_NAMES_U = { _key: OrderedDict([
    (unicode(_pk), _name) for (_pk, _name, _image) in getattr(django_settings, _key, [])
]) for _key in ['FAVORITE_CHARACTERS'] + getattr(django_settings, 'OTHER_CHARACTERS_KEYS', []) }


_CHARACTERS_LOCALIZED_NAMES_U = { _key: OrderedDict([
    (unicode(_pk), _names) for (_pk, _names) in getattr(django_settings, '{}_NAMES'.format(_key), {}).items()
]) for _key in ['FAVORITE_CHARACTERS'] + getattr(django_settings, 'OTHER_CHARACTERS_KEYS', []) }

def _getCharacterNameFromPk(key, pk):
    language = get_language()
    if language == 'en':
        return _CHARACTERS_NAMES_U[key].get(unicode(pk), None)
    return (_CHARACTERS_LOCALIZED_NAMES_U[key].get(unicode(pk), {}).get(language, None)
            or _CHARACTERS_NAMES_U[key].get(unicode(pk), None))

def _birthday_tags_per_characters_key(key):
    def _birthday_tag_name(pk, year):
        if BIRTHDAY_TAG:
            if not isinstance(BIRTHDAY_TAG, dict):
                return lambda: BIRTHDAY_TAG(pk, _getCharacterNameFromPk(key, pk), year)
            if BIRTHDAY_TAG.get(key, None):
                return lambda: BIRTHDAY_TAG[key](pk, _getCharacterNameFromPk(key, pk), year)
        return lambda: u'{}, {}! {}'.format(
            _('Happy Birthday'), _getCharacterNameFromPk(key, pk), year)
    tags = []
    try:
        start_year = LAUNCH_DATE.year
    except AttributeError:
        start_year = LAST_SERVER_RESTART.year
    for year in range(start_year, LAST_SERVER_RESTART.year + 2):
        collection_name = (
            (FAVORITE_CHARACTERS_MODEL.collection_name
             if FAVORITE_CHARACTERS_MODEL
             else 'character'
            ) if key == 'FAVORITE_CHARACTERS'
            else (OTHER_CHARACTERS_MODELS[key]['model'].collection_name
                  if isinstance(OTHER_CHARACTERS_MODELS[key], dict)
                  else OTHER_CHARACTERS_MODELS[key].collection_name)
        )
        for pk, birthday in getattr(django_settings, u'{}_BIRTHDAYS'.format(key), {}).items():
            if len(birthday) == 3:
                _birthday_year, birthday_month, birthday_day = birthday
            else:
                birthday_month, birthday_day = birthday
            utc_birthday_this_year = datetime.datetime(year, birthday_month, birthday_day, tzinfo=timezone.utc)
            # Tag can be seen if it ended already, or starts within the next 30 days
            if (utc_birthday_this_year < ((LAUNCH_DATE or LAST_SERVER_RESTART) - relativedelta(days=5))
                or getEventStatus(utc_birthday_this_year, starts_within=30) not in ['ended', 'starts_soon']):
                continue
            # Tag can be added to activities 5 days after the birthday
            start_date = utc_birthday_this_year - relativedelta(hours=9) # midnight Japan time is 9 hours before UTC
            end_date = start_date + relativedelta(days=5)
            tags.append(
                ('birthday-{}-{}-{}'.format(collection_name, pk, year), {
                    'translation': _birthday_tag_name(pk, year),
                    'start_date': start_date,
                    'end_date': end_date,
                    'character_pk': pk,
                })
            )
    return tags

def _birthday_tags():
    tags = []
    tags += _birthday_tags_per_characters_key('FAVORITE_CHARACTERS')
    for key, details in OTHER_CHARACTERS_MODELS.items():
        tags += _birthday_tags_per_characters_key(key)
    return tags

ACTIVITY_TAGS += _birthday_tags()

# Add seasonal tags

def _seasonal_tags():
    tags = []
    for season_name, season in SEASONS.items():
        tag = season.get('activity_tag', None)
        if tag:
            tags.append((
                u'season-{}'.format(season_name), {
                    'translation': tag,
                    'start_date': season.get('start_date', (01, 01)),
                    'end_date': season.get('end_date', (12, 31)),
                }
            ))
    return tags

ACTIVITY_TAGS += _seasonal_tags()

# Normalize activity tags format

_new_activity_tags = OrderedDict()
def _set_tag(tag_name, tag):
    if 'translation' not in tag:
        tag['translation'] = tag_name
    if not tag['translation']:
        if tag_name == 'unrelated':
            tag['translation'] = lambda: _('Not about {thing}').format(
                thing=GAME_NAME_PER_LANGUAGE.get(get_language(), GAME_NAME),
            )
        else:
            tag['translation'] = tag_name
    _new_activity_tags[tag_name] = tag

for _tag in ACTIVITY_TAGS:
    if isinstance(_tag, tuple) and isinstance(_tag[1], dict):
        _set_tag(_tag[0], _tag[1])
    elif isinstance(_tag, tuple):
        _set_tag(_tag[0], {
            'translation': _tag[1],
        })
    else:
        _set_tag(_tag, {})

ACTIVITY_TAGS = _new_activity_tags

# Permissions

_permissions_to_set = {
    'Disqus moderation': u'https://{}.disqus.com/admin/moderate/#/pending'.format(DISQUS_SHORTNAME),
    'See feedback form answers': FEEDBACK_FORM_ANSWERS,
    'Administrate the contributors on GitHub': u'https://github.com/{}/{}/settings/collaboration'.format(
        GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1]),
    'Administrate the moderators on Disqus': u'https://{}.disqus.com/admin/settings/moderators/'.format(
        DISQUS_SHORTNAME),
    'Receive private messages on Facebook': (
        u'https://facebook.com/{}/'.format(CONTACT_FACEBOOK)
        if CONTACT_FACEBOOK else None),
    'Receive private messages on Reddit': (u'https://www.reddit.com/user/{}/'.format(
        CONTACT_REDDIT) if CONTACT_REDDIT else None),
    'See event feedback form answers': EVENT_FEEDBACK_FORM_ANSWERS,
    'Administrate who can see the feedback form answers': EVENT_FEEDBACK_FORM_ANSWERS,
    'See event prizes form answers': EVENT_PRIZES_FORM_ANSWERS,
    'Administrate who can see the prizes form answers': EVENT_PRIZES_FORM_ANSWERS,
    'Edit wiki pages': 'https://github.com/{}/{}/wiki'.format(WIKI[0], WIKI[1]),
    'Repository': u'https://github.com/{}/{}/'.format(GITHUB_REPOSITORY[0], GITHUB_REPOSITORY[1]),
    'Bug tracker': BUG_TRACKER_URL,
}

now = timezone.now()
launched = LAUNCH_DATE is None or (LAUNCH_DATE is not True and LAUNCH_DATE < now)
for _group_name, _group in GROUPS:
    for _permission, _details in _group.get('outside_permissions', {}).items():
        if isinstance(_details, dict):
            if not _details.get('url', None):
                _details['url'] = _permissions_to_set.get(_permission, None)
            if not _details['url']:
                del(_group['outside_permissions'][_permission])
        elif not _details:
            _group['outside_permissions'][_permission] = _permissions_to_set.get(_permission, None)
            if not _group['outside_permissions'][_permission]:
                del(_group['outside_permissions'][_permission])
    if 'permissions' not in _group:
        _group['permissions'] = []
    # All staff groups have edit own staff profile
    if _group.get('requires_staff') and 'edit_own_staff_profile' not in _group['permissions']:
        _group['permissions'].append('edit_own_staff_profile')
    # All groups have beta test access + access site before launch
    if BETA_TEST_IN_PROGRESS and 'beta_test_features' not in _group['permissions']:
        _group['permissions'].append('beta_test_features')
    if launched and 'access_site_before_launch' in _group['permissions']:
        _group['permissions'].remove('access_site_before_launch')
    elif not launched and 'access_site_before_launch' not in _group['permissions']:
        _group['permissions'].append('access_site_before_launch')

# Enabled pages defaults

def _set_default_for_page(page_name, setting, value, on_none_disable=False):
    if page_name in ENABLED_PAGES:
        for page in (
                ENABLED_PAGES[page_name]
                if isinstance(ENABLED_PAGES[page_name], list)
                else [ENABLED_PAGES[page_name]]):
            if setting not in page:
                page[setting] = value
            if on_none_disable and not value:
                page['enabled'] = False

_wiki_page_description = lambda: u'{} - {}'.format(
    _('Help'), _('Learn a few tips and tricks to help you easily use {site}.').format(
        site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME)))

for _args in [
        ('about', 'page_description', SITE_LONG_DESCRIPTION),
        ('about_game', 'page_description', GAME_DESCRIPTION),
        ('map', 'page_description', lambda: _('Map of all {license} fans around the world.').format(
            license=GAME_NAME_PER_LANGUAGE.get(get_language(), GAME_NAME))),
        ('help', 'page_description', _wiki_page_description),
        ('wiki', 'page_description', _wiki_page_description),
        ('discord', 'redirect', COMMUNITY_DISCORD if COMMUNITY_DISCORD else None, True),
        ('twitter', 'redirect', 'https://twitter.com/{}'.format(TWITTER_HANDLE) if TWITTER_HANDLE else None, True),
        ('instagram', 'redirect', 'https://instagram.com/{}'.format(INSTAGRAM_HANDLE) if INSTAGRAM_HANDLE else None, True),
        ('facebook', 'redirect', 'https://facebook.com/{}'.format(FACEBOOK_HANDLE) if FACEBOOK_HANDLE else None, True),
]:
    _set_default_for_page(*_args)

# Sitemap pages for navbar

for _navbar_link_name, _navbar_link in ENABLED_NAVBAR_LISTS.items():
    if _navbar_link_name not in ENABLED_PAGES:
        ENABLED_PAGES[_navbar_link_name] = {
            'custom': False,
            'title': _navbar_link.get('title', _navbar_link_name.title()),
            'icon': _navbar_link.get('icon', None),
            'image': _navbar_link.get('image', None),
            'navbar_link': False,
            'template': 'sitemap',
            'function_name': 'sitemap',
        }
        if not ENABLED_PAGES[_navbar_link_name]['icon'] and not ENABLED_PAGES[_navbar_link_name]['image']:
            ENABLED_PAGES[_navbar_link_name]['icon'] = 'category'
