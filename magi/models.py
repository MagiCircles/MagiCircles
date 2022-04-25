import hashlib, urllib, datetime, pytz
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.utils.translation import gettext_lazy as _, get_language
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.formats import date_format
from django.forms.models import model_to_dict
from django.conf import settings as django_settings
from magi.utils import (
    AttrDict,
    getMagiCollection,
    getEventStatus,
    uploadToRandom,
    uploadItem,
    uploadTiny,
    linkToImageURL,
    hasGroup,
    hasPermission,
    hasOneOfPermissions,
    hasPermissions,
    toHumanReadable,
    locationOnChange,
    staticImageURL,
    birthdayURL,
    hasPermissionToMessage,
    ordinalNumber,
    getAge,
    simplifyMarkdown,
    getCharactersChoices,
    getCharacterNameFromPk,
    getCharacterImageFromPk,
    getCharacterURLFromPk,
    getCharactersFavoriteFields,
    NATIVE_LANGUAGES,
    LANGUAGES_DICT,
)
from magi.settings import (
    ACCOUNT_MODEL,
    COLOR,
    SITE_STATIC_URL,
    DONATORS_STATUS_CHOICES,
    USER_COLORS,
    SITE_URL,
    SITE_NAME,
    SITE_NAME_PER_LANGUAGE,
    ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT,
    ACTIVITY_TAGS,
    GROUPS,
    HOME_ACTIVITY_TABS,
    MINIMUM_LIKES_POPULAR,
    DONATORS_GOAL,
    EXTRA_PREFERENCES,
    USERS_REPUTATION_CALCULATOR,
    GOOD_REPUTATION_THRESHOLD,
    PROFILE_BACKGROUNDS_IMAGES,
)
from magi.raw import other_sites
from magi.polyfills import string_concat
from magi.item_model import (
    MagiModel,
    BaseMagiModel,
    get_image_url,
    i_choices,
    addMagiModelProperties,
    getInfoFromChoices,
    ALL_LANGUAGES,
    ALL_ALT_LANGUAGES,
    UserImage,
)
from magi.abstract_models import CacheOwner
from magi.default_settings import RAW_CONTEXT

Account = ACCOUNT_MODEL

############################################################
# Utils

def avatar(user, size=200):
    """
    Preferences in user objects must always be prefetched
    """
    default = staticImageURL('avatar.png', full=True)
    if (getattr(django_settings, 'DEBUG', False)
        and getattr(django_settings, 'UPLOADED_FILES_URL', None)):
        default = staticImageURL('avatar.png', static_url=u'{}{}static/'.format(
            'https:' if 'http' not in django_settings.UPLOADED_FILES_URL else '',
            django_settings.UPLOADED_FILES_URL,
        ))
    if hasattr(django_settings, 'DEBUG_AVATAR'):
        default = django_settings.DEBUG_AVATAR
    if user.preferences.twitter:
        default = u'{}twitter_avatar/{}/'.format(SITE_URL if SITE_URL.startswith('http') else 'https:' + SITE_URL, user.preferences.twitter)
    return ("https://www.gravatar.com/avatar/"
            + hashlib.md5(user.email.lower()).hexdigest()
            + "?" + urllib.urlencode({'d': default, 's': str(size)}))

############################################################
# Add MagiModel properties to User objects

addMagiModelProperties(User, 'user')
User.image_url = property(avatar)
User.http_image_url = property(avatar)
User.owner_id = property(lambda u: u.id)
User.owner = property(lambda u: u)
User.report_sentence = property(lambda u: _('Report {thing}').format(thing=u.username))
User.hasGroup = lambda u, group: hasGroup(u, group)
User.hasPermission = lambda u, permission: hasPermission(u, permission)
User.hasOneOfPermissions = lambda u, permissions: hasOneOfPermissions(u, permissions)
User.hasPermissions = lambda u, permissions: hasPermissions(u, permissions)

User.birthday_url = property(lambda u: birthdayURL(u))
User.hasPermissionToMessage = hasPermissionToMessage

############################################################

ACTIVITY_TAGS_CHOICES = [
    (_tag_name, _tag['translation'])
    for _tag_name, _tag in ACTIVITY_TAGS.items()
]

ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT = [
    _tag_name
    for _tag_name, _tag in ACTIVITY_TAGS.items()
    if _tag.get('hidden_by_default', False)
]

############################################################
# User preferences

class UserPreferences(BaseMagiModel):
    user = models.OneToOneField(User, related_name='preferences', on_delete=models.CASCADE)

    LANGUAGE_CHOICES = NATIVE_LANGUAGES.items()
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = True
    i_language = models.CharField(_('Language'), max_length=10)

    _cache_description = models.TextField(null=True)
    m_description = models.TextField(_('Description'), null=True, blank=True)

    favorite_character1 = models.CharField(null=True, max_length=200)
    favorite_character2 = models.CharField(null=True, max_length=200)
    favorite_character3 = models.CharField(null=True, max_length=200)
    color = models.CharField(_('Color'), max_length=100, null=True, blank=True)
    birthdate = models.DateField(_('Birthdate'), blank=True, null=True)
    show_birthdate_year = models.BooleanField(_('Display your birthdate year'), default=True)
    default_tab = models.CharField(_('Default tab'), max_length=100, null=True)
    location = models.CharField(_('Location'), max_length=200, null=True, blank=True, help_text=string_concat(_('The city you live in.'), ' ', _('It might take up to 24 hours to update your location on the map.')))

    LOCATION_ON_CHANGE = locationOnChange

    location_changed = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    @property
    def location_url(self):
        latlong = '{},{}'.format(self.latitude, self.longitude) if self.latitude else None
        return u'/map/?center={}&zoom=10'.format(latlong) if latlong else u'https://www.google.com/maps?q={}'.format(self.location)

    following = models.ManyToManyField(User, related_name='followers')

    # Activities preferences

    DEFAULT_ACTIVITIES_TABS = HOME_ACTIVITY_TABS
    DEFAULT_ACTIVITIES_TAB_CHOICES = [(_k, _v['title']) for _k, _v in HOME_ACTIVITY_TABS.items()]
    DEFAULT_ACTIVITIES_TAB_SOFT_CHOICES = True
    i_default_activities_tab = models.PositiveIntegerField(_('Default tab'), default=0)
    default_activities_tab_form_fields = property(getInfoFromChoices('default_activities_tab', HOME_ACTIVITY_TABS, 'form_fields'))

    ACTIVITIES_LANGUAGE_CHOICES = ALL_LANGUAGES
    ACTIVITIES_LANGUAGE_WITHOUT_I_CHOICES = True
    ACTIVITIES_LANGUAGE_SOFT_CHOICES = True
    i_activities_language = models.CharField(_('Always post activities in {language}'), max_length=10)

    STATUS_CHOICES = DONATORS_STATUS_CHOICES if DONATORS_STATUS_CHOICES else (
        ('THANKS', 'Thanks'),
        ('SUPPORTER', _('Player')),
        ('LOVER', _('Super Player')),
        ('AMBASSADOR', _('Extreme Player')),
        ('PRODUCER', _('Master Player')),
        ('DEVOTEE', _('Ultimate Player')),
    )

    STATUS_COLORS = {
        'SUPPORTER': '#4a86e8',
        'LOVER': '#ff53a6',
        'AMBASSADOR': '#a8a8a8',
        'PRODUCER': '#c98910',
        'DEVOTEE': '#c98910',
    }

    STATUS_WITHOUT_I_CHOICES = True
    STATUS_SOFT_CHOICES = True
    i_status = models.CharField('Status', max_length=12, null=True)
    @property
    def status_color(self):
        return self.STATUS_COLORS[self.i_status] if self.i_status else None

    donation_link = models.CharField(_('Custom link'), max_length=200, null=True, blank=True, validators=[
        validators.URLValidator(),
    ])
    donation_link_title = models.CharField(_('Title'), max_length=100, null=True, blank=True)

    @property
    def is_premium(self):
        return self.status and self.status != 'THANKS'

    view_activities_language_only = models.BooleanField(_('View activities in your language only?'), default=ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT)
    email_notifications_turned_off_string = models.CharField(max_length=15, null=True)
    invalid_email = models.BooleanField(default=False)

    GROUPS_CHOICES = [(_k, _v['translation']) for _k, _v in GROUPS]
    GROUPS = OrderedDict(GROUPS)
    c_groups = models.TextField(_('Roles'), blank=True, null=True)
    j_settings_per_groups = models.TextField(null=True)

    @property
    def t_settings_per_groups(self):
        s = {
            group: {
                toHumanReadable(setting): value
                for setting, value in settings.items()
            }
            for group, settings in (self.settings_per_groups or {}).items()
        }
        if 'translator' in s and 'Languages' in s['translator']:
            s['translator']['Languages'] = u', '.join([
                str(LANGUAGES_DICT.get(l, l)) for l in s['translator']['Languages']
            ])
        return s

    @property
    def groups_and_details(self):
        return OrderedDict([
            (group, self.GROUPS[group])
            for group in self.groups
            if group in self.GROUPS
        ])

    HIDDEN_TAGS = ACTIVITY_TAGS
    HIDDEN_TAGS_CHOICES = ACTIVITY_TAGS_CHOICES
    d_hidden_tags = models.TextField(_('Hide tags'), null=True)

    blocked = models.ManyToManyField(User, related_name='blocked_by')

    last_bump_counter = models.PositiveIntegerField(default=0)
    last_bump_date = models.DateTimeField(null=True)

    PRIVATE_MESSAGE_SETTINGS_CHOICES = (
        ('anyone', _('Anyone')),
        ('follow', _('Only people I follow')),
        ('nobody', _('Nobody')),
    )
    i_private_message_settings = models.PositiveIntegerField(_('Who is allowed to send you private messages?'), default=0, choices=i_choices(PRIVATE_MESSAGE_SETTINGS_CHOICES))

    EXTRA_CHOICES = EXTRA_PREFERENCES
    EXTRA_SOFT_CHOICES = True
    EXTRA_CHOICES_KEYS_AS_LABELS = True
    d_extra = models.TextField(blank=True, null=True)

    @property
    def favorite_characters(self):
        return [c for c in [
            self.favorite_character1,
            self.favorite_character2,
            self.favorite_character3,
        ] if c]

    @property
    def background_id(self): return int(self.extra.get('background', '0')) or None

    @property
    def background_image_url(self):
        return staticImageURL(PROFILE_BACKGROUNDS_IMAGES.get(self.background_id, None))

    @classmethod
    def get_localized_color(self, color):
        if color and USER_COLORS:
            try:
                return (_(localized) for (name, localized, __, __) in USER_COLORS if str(name) == color).next()
            except: pass
        return ''
    @property
    def localized_color(self):
        return type(self).get_localized_color(self.color)

    @classmethod
    def get_hex_color(self, color):
        if color and USER_COLORS:
            try:
                return (hex for (name, _, _, hex) in USER_COLORS if str(name) == color).next()
            except: pass
        return COLOR
    @property
    def hex_color(self):
        return type(self).get_hex_color(self.color)

    @classmethod
    def get_rgb_color(self, color):
        return tuple(int(self.get_hex_color(color).lstrip('#')[i:i+2], 16) for i in (0, 2 ,4))
    @property
    def rgb_color(self):
        return type(self).get_rbg_color(self.color)

    @classmethod
    def get_css_color(self, color):
        if color and USER_COLORS:
            try:
                return (css_color for (name, _, css_color, _) in USER_COLORS if str(name) == color).next()
            except: pass
        return 'main'

    @property
    def css_color(self):
        return type(self).get_css_color(self.color)

    @classmethod
    def get_age(self, birthdate):
        return getAge(birthdate)

    @property
    def age(self):
        return type(self).get_age(self.birthdate)

    @property
    def formatted_age(self):
        return getAge(self.birthdate, formatted=True)

    @property
    def formatted_birthday_date(self):
        return date_format(self.birthdate, format='MONTH_DAY_FORMAT', use_l10n=True) if self.birthdate else ''
    @property
    def formatted_birthday(self):
        if not self.birthdate: return ''
        if self.show_birthdate_year:
            return u'{} ({})'.format(
                date_format(self.birthdate, format='DATE_FORMAT', use_l10n=True),
                self.formatted_age,
            )
        return self.formatted_birthday_date

    @property
    def email_notifications_turned_off(self):
        if not self.email_notifications_turned_off_string:
            return []
        return [Notification.MESSAGES[int(t)][0] for t in self.email_notifications_turned_off_string.split(',')]

    def is_notification_email_allowed(self, notification_type):
        if self.invalid_email:
            return False
        for type in self.email_notifications_turned_off:
            if type == notification_type:
                return False
        return True

    def save_email_notifications_turned_off(self, turned_off):
        """
        Will completely replace any existing list of turned off email notifications.
        """
        self.email_notifications_turned_off_string = ','.join([str(i) for i in turned_off])

    # Cache tabs
    _cache_j_tabs_with_content = models.TextField(null=True)
    _cache_tabs_with_content_update_on_none = True

    def to_cache_tabs_with_content(self):
        tabs_with_content = {}

        # Badges
        badge_collection = getMagiCollection('badge')
        if badge_collection:
            tabs_with_content['badge'] = bool(badge_collection.queryset.filter(user_id=self.user_id).count())
            tabs_with_content['badge_top_profile'] = bool(badge_collection.queryset.filter(
                user_id=self.user_id, show_on_top_profile=True).count())

        # Accounts and tabs per accounts
        account_ids = list(ACCOUNT_MODEL.objects.filter(owner=self.user_id).values_list('id', flat=True))
        tabs_with_content['account'] = {
            'has_content': bool(len(account_ids)),
            'tabs_per_account': {
                account_id: {
                    collection_name: bool(collection.queryset.filter(account_id=account_id).count())
                    for collection_name, collection in RAW_CONTEXT['collectible_collections'].get(
                            'account', {}).items()
                } for account_id in account_ids
            },
        }

        # Collections as_profile_tab + collectibles per owner
        tabs_with_content.update({
            collection_name: bool(collection.queryset.filter(**{
                collection.queryset.model.selector_to_owner(): self.user_id,
            }).count()) for collection_name, collection in [
                (collection_name, getMagiCollection(collection_name))
                for collection_name in RAW_CONTEXT['collections_in_profile_tabs']
            ] + RAW_CONTEXT['collectible_collections'].get('owner', {}).items()
        })

        return tabs_with_content

    # Cache twitter
    _cache_twitter = models.CharField(max_length=32, null=True, blank=True) # changed when links are modified

    @property
    def twitter(self):
        return self._cache_twitter

    # Cache blocked
    _cache_c_blocked_ids = models.TextField(null=True) # changed when blocked are modified
    _cache_c_blocked_by_ids = models.TextField(null=True) # changed when blocked of other user are modified

    def to_cache_blocked_ids(self):
        return self.blocked.all().values_list('id', flat=True)

    def to_cache_blocked_by_ids(self):
        return User.objects.filter(preferences__blocked__id=self.user_id).values_list('id', flat=True)

    @classmethod
    def cached_blocked_ids_map(self, i):
        return int(i)

    cached_blocked_by_ids_map = cached_blocked_ids_map

    # Cached reputation score
    _cache_reputation_days = 1
    _cache_reputation_last_update = models.DateTimeField(null=True)
    _cache_reputation = models.IntegerField(null=True, db_index=True)

    def reputation_points(self):
        # Reputation deal breakers
        if self.invalid_email:
            return {
                'invalid_email': (0, 0),
            }

        now = timezone.now()
        five_days_ago = now - relativedelta(days=5)
        six_months_ago = now - datetime.timedelta(days=30 * 6)
        reputation_points = {
            'joined_5_days_ago': (int(self.user.date_joined <= five_days_ago), 10),
            'joined_6_months_ago': (int(self.user.date_joined <= six_months_ago), 50),
            'total_following': (self.following.count(), 1),
            'total_followers': (self.user.followers.count(), 5),
            'total_activities': (self.user.activities.count(), 2),
            'total_accounts': (self.user.accounts.count(), 1),
            'total_reported_item': (
                Report.objects.filter(
                    reported_thing_owner_id=self.user_id,
                    i_status__in=[
                        Report.get_i('status', 'Deleted'),
                        Report.get_i('status', 'Edited'),
                    ],
                    modification__gte=six_months_ago,
                ).count(), -1),
        }
        if USERS_REPUTATION_CALCULATOR:
            reputation_points = USERS_REPUTATION_CALCULATOR(reputation_points)
        return reputation_points

    def to_cache_reputation(self):
        return sum([total * points for total, points in self.reputation_points().values()])

    @property
    def has_good_reputation(self):
        return self.cached_reputation >= GOOD_REPUTATION_THRESHOLD

    # Cached unread notifications
    _cache_unread_notifications_days = 5
    _cache_unread_notifications_last_update = models.DateTimeField(null=True)
    _cache_unread_notifications = models.PositiveIntegerField(default=0)

    def to_cache_unread_notifications(self):
        return self.user.notifications.filter(seen=False).count()

    class Meta:
        verbose_name_plural = "list of userpreferences"

############################################################
# User links

class UserLink(BaseMagiModel):
    alphanumeric = validators.RegexValidator(r'^[0-9a-zA-Z\-_\. /]*$', 'Only alphanumeric and - _ characters are allowed.')
    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='links', on_delete=models.CASCADE)
    value = models.CharField(string_concat(_('Username'), '/', _('ID')), max_length=64, help_text=_('Write your username only, no URL.'), validators=[alphanumeric])

    TYPE_CHOICES = [
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
        ('reddit', 'Reddit'),
    ] + [
        (_details['shortname'], _details['name'])
        for _details in other_sites
        if _details['name'] != SITE_NAME and _details.get('shortname', None)
    ] + [
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('tumblr', 'Tumblr'),
        ('twitch', 'Twitch'),
        ('steam', 'Steam'),
        ('osu', 'osu!'),
        ('pixiv', 'Pixiv'),
        ('deviantart', 'DeviantArt'),
        ('crunchyroll', 'Crunchyroll'),
        ('mal', 'MyAnimeList'),
        ('animeplanet', 'Anime-Planet'),
        ('myfigurecollection', 'MyFigureCollection'),
        ('line', 'LINE Messenger'),
        ('github', 'GitHub'),
        ('carrd', 'Carrd'),
        ('listography', 'Listography'),
    ]

    TYPE_WITHOUT_I_CHOICES = True
    TYPE_SOFT_CHOICES = True
    i_type = models.CharField(_('Platform'), max_length=20)

    RELEVANCE_CHOICES = (
        _('Never'),
        _('Sometimes'),
        _('Often'),
        _('Every single day'),
    )

    i_relevance = models.PositiveIntegerField(choices=i_choices(RELEVANCE_CHOICES), null=True, blank=True)

    LINK_URLS = {
        'Location': u'http://maps.google.com/?q={}',
        'twitter': u'http://twitter.com/{}',
        'facebook': u'https://www.facebook.com/{}',
        'reddit': u'http://www.reddit.com/user/{}',
        'instagram': u'https://instagram.com/{}/',
        'youtube': u'https://www.youtube.com/{}',
        'tumblr': u'http://{}.tumblr.com/',
        'twitch': u'http://twitch.tv/{}',
        'steam': u'http://steamcommunity.com/id/{}',
        'osu': u'https://osu.ppy.sh/u/{}',
        'pixiv': u'https://pixiv.me/{}',
        'deviantart': u'https://{}.deviantart.com/',
        'crunchyroll': u'http://www.crunchyroll.com/user/{}',
        'mal': u'https://myanimelist.net/profile/{}',
        'animeplanet': u'https://www.anime-planet.com/users/{}',
        'myfigurecollection': u'https://myfigurecollection.net/profile/{}',
        'line': u'http://line.me/#{}',
        'github': u'https://github.com/{}',
        'carrd': u'https://{}.carrd.co/',
        'listography': u'https://listography.com/{}',
    }
    LINK_URLS.update({
        (_details['shortname'], _details['profile_url'])
        for _details in other_sites
        if _details['name'] != SITE_NAME and _details.get('shortname', None)
    })

    @property
    def url(self):
        if self.i_type in self.LINK_URLS:
            return self.LINK_URLS[self.i_type].format(self.value)
        return '#'

    @property
    def image_url(self):
        if self.i_type in self.LINK_URLS:
            return linkToImageURL(self)
        return None

############################################################
# Staff Configuration

class StaffConfiguration(MagiModel):
    collection_name = 'staffconfiguration'

    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='added_configurations', on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    verbose_key = models.CharField('Name', max_length=100)
    value = models.TextField('Value', null=True)

    LANGUAGE_CHOICES = ALL_LANGUAGES
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = True
    i_language = models.CharField(_('Language'), max_length=10, null=True)
    language_image_url = property(lambda _s: staticImageURL(_s.language, folder=u'language', extension='png'))

    is_long = models.BooleanField(default=False)
    is_markdown = models.BooleanField(default=False)
    is_boolean = models.BooleanField(default=False)

    # Owner is always pre-selected
    @property
    def cached_owner(self):
        self.owner.unicode = str(self.owner)
        return self.owner

    @property
    def boolean_value(self):
        if self.is_boolean:
            if self.value == 'True':
                return True
            if self.value == 'False':
                return False
            return None
        return self.value

    @property
    def representation_value(self):
        if self.is_markdown:
            return u'<div class="list-group-item to-markdown">{}</div>'.format(self.value) if self.value else ''
        elif self.is_boolean:
            if self.value == 'True':
                return u'<i class="flaticon-checked"></i>'
            if self.value == 'False':
                return u'<i class="flaticon-delete"></i>'
            return ''
        elif self.field_type == 'image':
            return staticImageURL(self.value)
        return self.value or ''

    @property
    def field_type(self):
        if self.key.endswith('_image_url') or self.key.endswith('_image'):
            return 'image'
        if self.is_markdown or self.is_boolean:
            return 'html'
        return 'text'

    def __unicode__(self):
        return self.verbose_key

    class Meta:
        unique_together = (('key', 'i_language'),)
        ordering = ['id']

############################################################
# Staff details

class StaffDetails(MagiModel):
    collection_name = 'staffdetails'

    owner = models.OneToOneField(User, related_name='staff_details', on_delete=models.CASCADE, unique=True)

    discord_username = models.CharField('Discord username', max_length=100, null=True)
    preferred_name = models.CharField('What would you prefer to be called?', max_length=100, null=True)
    pronouns = models.CharField('Preferred pronouns', max_length=32, null=True)

    image = models.ImageField(
        _('Image'), upload_to=uploadToRandom('staff_photos'), null=True, blank=True,
        help_text='Photograph of yourself. Real life photos look friendlier when we introduce the team. If you really don\'t want to show your face, you can use an avatar, but we prefer photos :)',
    )
    description = models.TextField('Self introduction', help_text='You can use markdown to add links.', null=True)

    favorite_food = models.CharField(max_length=100, null=True)
    FAVORITE_FOODS_CHOICES = ALL_ALT_LANGUAGES
    d_favorite_foods = models.TextField(_('Liked food'), null=True)

    hobbies = models.CharField(max_length=100, null=True)
    HOBBIESS_CHOICES = ALL_ALT_LANGUAGES
    d_hobbiess = models.TextField(_('hobbies'), null=True)

    nickname = models.CharField('Super hero / Rock star name', null=True, max_length=100)
    c_hashtags = models.CharField('Hashtags that describe yourself', help_text='Separate with comma', null=True, max_length=200)
    staff_since = models.DateField('Staff since', null=True)

    TIMEZONE_CHOICES = pytz.common_timezones
    i_timezone = models.PositiveIntegerField('Timezone', choices=i_choices(TIMEZONE_CHOICES), null=True)

    AVAILABILITY_CHOICES = [(_a, _a.replace('-', ' - ').replace('am', ' am').replace('pm', ' pm')) for _a in [
        '6am-8am','8am-10am','10am-noon','noon-2pm','2pm-4pm',
        '4pm-6pm','6pm-8pm','8pm-10pm', '10pm-midnight','midnight-2am', '2am-6am',
    ]]
    WEEKEND_AVAILABILITY_CHOICES = AVAILABILITY_CHOICES
    d_availability = models.TextField('When do you plan to perform your staff tasks on WEEKDAYS (Monday to Friday)? (in your timezone)', null=True)
    d_weekend_availability = models.TextField('When do you plan to perform your staff tasks on WEEKENDS (Saturday and Sunday)? (in your timezone)', null=True)
    availability_details = models.TextField('Availability details', null=True, help_text='if your schedule doesn\'t match the weekdays / weekends schema')

    _I_TO_T_AVAILABILITY = dict(i_choices(AVAILABILITY_CHOICES, translation=True))
    _I_TO_AVAILABILITY = dict(i_choices(AVAILABILITY_CHOICES, translation=False))
    _AVAILABILITY_TO_I = { _v: _k for _k, _v in i_choices(AVAILABILITY_CHOICES, translation=False) }

    @property
    def availability_calendar(self):
        calendar = [['', 'M', 'T', 'W', 'T', 'F', 'S', 'S']] + [
            [self._I_TO_AVAILABILITY[i] if j == 0 else 'no' for j in range(8)]
            for i in range(len(self.AVAILABILITY_CHOICES))
        ]
        for a, v in self.availability.items():
            if v:
                for i in range(5):
                    calendar[self._AVAILABILITY_TO_I[a]][i + 1] = 'yes'
        for a, v in self.weekend_availability.items():
            if v:
                for i in range(5, 7):
                    calendar[self._AVAILABILITY_TO_I[a]][i + 1] = 'yes'
        return calendar

    def _strtime_to_int(self, time):
        time = time.replace('am', '')
        if time == 'midnight':
            time = 0
        elif time == 'noon':
            time = 12
        elif 'pm' in time:
            time = int(time.replace('pm', '')) + 12
        else:
            time = int(time)
        return time

    def _int_to_strtime(self, integer):
        if integer == 0 or integer == 24:
            return 'midnight'
        elif integer == 12:
            return 'noon'
        if integer > 12:
            return u'{} pm'.format(integer - 12)
        return u'{} am'.format(integer)

    def _hour_timezone_convert(self, hour, other_timezone):
        today = datetime.datetime.today()
        past_monday = today - datetime.timedelta(days=today.weekday())
        new_date = past_monday.replace(hour=hour, tzinfo=pytz.timezone(self.timezone))
        new_date_with_other_timezone = new_date.astimezone(pytz.timezone(other_timezone))
        return new_date_with_other_timezone.hour

    def _availability_time_to_timezone(self, time, other_timezone):
        new_time = []
        for time in time.split('-'):
            integer_time = self._strtime_to_int(time)
            integer_other_timezone = self._hour_timezone_convert(integer_time, other_timezone)
            strtime_other_timezone = self._int_to_strtime(integer_other_timezone)
            new_time.append(strtime_other_timezone)
        return ' - '.join(new_time)

    def availability_calendar_timezone(self, other_timezone=None):
        weekdays = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
        if self.timezone and other_timezone:
            padding = 2
            weekdays = [self.timezone.split('/')[-1], other_timezone.split('/')[-1]] + weekdays
            def to_default_value(i, j):
                if j == 0:
                    return self._I_TO_T_AVAILABILITY[i]
                elif j == 1:
                    return self._availability_time_to_timezone(self._I_TO_AVAILABILITY[i], other_timezone)
                return 'no'
        else:
            padding = 1
            weekdays = [self.timezone.split('/')[-1] if self.timezone else ''] + weekdays
            def to_default_value(i, j):
                if j == 0:
                    return self._I_TO_AVAILABILITY[i]
                return 'no'
        calendar = [weekdays] + [
            [to_default_value(i, j) for j in range(7 + padding)]
            for i in range(len(self.AVAILABILITY_CHOICES))
        ]
        for a, v in self.availability.items():
            if v:
                for i in range(5):
                    calendar[self._AVAILABILITY_TO_I[a] + 1][i + padding] = 'yes'
        for a, v in self.weekend_availability.items():
            if v:
                for i in range(5, 7):
                    calendar[self._AVAILABILITY_TO_I[a] + 1][i + padding] = 'yes'
        return calendar

    @property
    def availability_calendar(self):
        return self.availability_calendar_timezone()

    def _hour_to_closest_timerange(self, hour):
        if hour % 2:
            hour -= 1
        if hour > 2 and hour < 6:
            hour = 2
        if hour == 2:
            next_hour = 6
        else:
            next_hour = (hour + 2) % 24
        strtime = self._int_to_strtime(hour)
        strtime_next = self._int_to_strtime(next_hour)
        return u'{}-{}'.format(strtime.replace(' ', ''), strtime_next.replace(' ', ''))

    @property
    def available_now(self):
        if not self.timezone:
            return None
        today = datetime.datetime.today().replace(tzinfo=pytz.utc)
        date_of_timezone = today.astimezone(pytz.timezone(self.timezone))
        timerange = self._hour_to_closest_timerange(date_of_timezone.hour)
        if date_of_timezone.weekday() < 5:
            return bool(self.availability.get(timerange, False))
        return bool(self.weekend_availability.get(timerange, False))

    experience = models.TextField('Experience with the community', null=True, help_text='What are your previous/current experiences as an admin, moderator or middleman in the game\'s community or similar?')
    other_experience = models.TextField('Other experience', null=True, help_text='Other relevant experience as an admin/moderator, your professional background, education, experience working with people, managing social networks, etc.')

    PUBLIC_FIELDS = ['image', 'description', 'favorite_food', 'hobbies', 'nickname', 'c_hashtags', 'preferred_name', 'pronouns', 'timezone']
    STAFF_ONLY_FIELDS = ['discord_username', 'staff_since', 'availability', 'weekend_availability', 'experience', 'other_experience']

    def __unicode__(self):
        return u'{} staff details'.format(self.owner.username)

############################################################
# Activity

class Activity(MagiModel):
    collection_name = 'activity'

    creation = models.DateTimeField(auto_now_add=True)
    last_bump = models.DateTimeField(db_index=True, null=True)
    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='activities', db_index=True, on_delete=models.CASCADE)
    m_message = models.TextField(_('Message'), null=True)

    likes = models.ManyToManyField(User, related_name="liked_activities")

    LANGUAGE_CHOICES = NATIVE_LANGUAGES.items()
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = True
    i_language = models.CharField(_('Language'), max_length=10)
    language_image_url = property(lambda _s: staticImageURL(_s.language, folder=u'language', extension='png'))

    TAGS = ACTIVITY_TAGS
    TAGS_CHOICES = ACTIVITY_TAGS_CHOICES
    c_tags = models.TextField(_('Tags'), blank=True, null=True)

    _original_image = models.ImageField(null=True, upload_to=uploadTiny('activities'))
    image = models.ImageField(_('Image'), upload_to=uploadToRandom('activities'), null=True, blank=True, help_text=_('Only post official artworks, artworks you own, or fan artworks that are approved by the artist and credited.'))

    archived_by_owner = models.BooleanField(default=False)
    archived_by_staff = models.ForeignKey(User, related_name='archived_activities', null=True, on_delete=models.SET_NULL)

    @property
    def archived(self):
        return self.archived_by_owner or self.archived_by_staff

    def has_permissions_to_archive(self, user):
        # If you're the owner and it's older than a month, you can archive
        # If you're premium, the one month limit doesn't apply
        # Returns: (has_permissions, because_premium)
        a_month_ago = timezone.now() - datetime.timedelta(days=30)
        if not user.is_authenticated() or not self.is_owner(user):
            return (False, False)
        if user.preferences.is_premium:
            return (True, True)
        elif self.creation < a_month_ago:
            return (True, False)
        return (False, False)

    def has_permissions_to_ghost_archive(self, user):
        # If you have the manipulate_activities permission
        return (user.is_authenticated()
                and not self.is_owner(user)
                and user.hasPermission('manipulate_activities'))

    @property
    def is_popular(self):
        return self.cached_total_likes >= MINIMUM_LIKES_POPULAR

    @property
    def is_staff_picks(self):
        return 'staff' in self.tags

    @property
    def can_dynamically_load_items(self):
        for tag in self.tags:
            if tag in ['news', 'staff']:
                return True
        return False

    tinypng_settings = {
        'image': {
            'resize': 'scale',
            'width': 890,
            'use_tinypng': False,
        }
    }

    # Cache

    # Updated manually when activity is updated
    _cache_message = models.TextField(null=True)

    # Updated manually when activity is updated
    _cache_hidden_by_default = models.BooleanField(default=False, db_index=True)

    def to_cache_hidden_by_default(self):
        return bool([True for tag in self.tags if tag in ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT])

    # Updated manually when someone likes or unlikes the activity
    _cache_total_likes_update_on_none = True
    _cache_total_likes = models.PositiveIntegerField(null=True)

    def to_cache_total_likes(self):
        return self.likes.count()

    # Updated manually on user edited on user edited
    # or auto updated when cached_owner is accessed and cache older than 20d
    _cache_days = 20
    _cache_last_update = models.DateTimeField(null=True)
    _cache_owner_username = models.CharField(max_length=32, null=True)
    _cache_owner_email = models.EmailField(blank=True)
    _cache_owner_preferences_i_status = models.CharField(max_length=12, null=True)
    _cache_owner_preferences_twitter = models.CharField(max_length=32, null=True, blank=True)

    def force_cache_owner(self):
        """
        Recommended to use select_related('owner', 'owner__preferences') when calling this method
        """
        self._cache_last_update = timezone.now()
        self._cache_owner_username = self.owner.username
        self._cache_owner_email = self.owner.email
        self._cache_owner_preferences_i_status = self.owner.preferences.i_status
        self._cache_owner_preferences_twitter = self.owner.preferences.twitter
        saveActivityCacheOwnerWithoutChangingModification(self)

    @property
    def cached_owner(self):
        now = timezone.now()
        if not self._cache_last_update or self._cache_last_update < now - datetime.timedelta(days=self._cache_days):
            self.force_cache_owner()
        cached_owner = AttrDict({
            'pk': self.owner_id,
            'id': self.owner_id,
            'username': self._cache_owner_username,
            'email': self._cache_owner_email,
            'item_url': '/user/{}/{}/'.format(self.owner_id, self._cache_owner_username),
            'ajax_item_url': '/ajax/user/{}/'.format(self.owner_id),
            'preferences': AttrDict({
                'i_status': self._cache_owner_preferences_i_status,
                'status': dict(UserPreferences.STATUS_CHOICES).get(self._cache_owner_preferences_i_status, None),
                'status': self._cache_owner_preferences_i_status,
                'status_color': dict(UserPreferences.STATUS_COLORS).get(self._cache_owner_preferences_i_status, None),
                't_status': dict(UserPreferences.STATUS_CHOICES).get(self._cache_owner_preferences_i_status, None),
                'is_premium': self._cache_owner_preferences_i_status and self._cache_owner_preferences_i_status != 'THANKS',
                'twitter': self._cache_owner_preferences_twitter,
            }),
        })
        return cached_owner

    @property
    def shareSentence(self):
        return _(u'Check out {username}\'s activity on {site}: {activity}').format(
            username=self.cached_owner.username,
            site=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
            activity=self.summarize(40),
        )

    def summarize(self, length=100):
        """
        Return the first {length} characters without cutting words
        """
        return simplifyMarkdown(self.m_message, max_length=length)

    def get_first_image(self):
        if self.image:
            return self.http_image_url
        try:
            return self.m_message.split('![')[1].split('](')[1].split(')')[0] or None
        except IndexError:
            return None

    m_description = property(lambda _s: _s.m_message)

    def __unicode__(self):
        return self.summarize()

    class Meta:
        verbose_name_plural = 'activities'
        ordering = ['-last_bump']

############################################################
# Activities utilities

_CHOOSE_HIDDEN_TAGS_MESSAGE = _('You can change which tags you would like to see or hide in your settings.')

def getAllowedTags(
        request,
        is_creating=False, force_allow=None, check_hidden_by_user=True,
        check_permissions_to_show=True,
        return_allowed=True, return_not_allowed=False,
        as_dict=False, full_tags=False,
):
    """
    By default, returns a list of tuples that can be used as models/forms choices.
    Full tags can be returned with full_tags=True.
    A dict instead of list of tuples can be returned with as_dict=True.

    By default, checks everything except permissions related to adding a tag.
    is_creating=True will additionally check permissions to be added + if the tag is current.
    Some permissions can be disabled:
    - check_hidden_by_user=False
    - check_permissions_to_show=False
    It's not possible to disable check for Future tags.

    By default, returns the list of allowed tags.
    Tags not allowed alongside reasons can be returned with return_not_allowed=True.
    If you only want the tags not allowed, you can also add return_allowed=False.

    Tags can be forcefully allowed with force_allow (a list of strings).
    """
    not_allowed_tags_and_reasons = {}
    tag_statuses = {}
    def notAllowedReason(tag_name, tag, reason, verbose_reason=None):
        not_allowed_tags_and_reasons[tag_name] = (tag, u'{} {}'.format(
            _(u'You are not allowed to see activities with the tag "{tag}".').format(
                tag=tag['translation']() if callable(tag['translation']) else tag['translation'],
            ), verbose_reason or ''), reason)
    def isTagAllowed(tag_name, tag):
        tag_statuses[tag_name] = getEventStatus(
            tag.get('start_date', None),
            tag.get('end_date', None),
            without_year_return='ended',
        )
        # Force allowed will bypass checks
        if tag_name in (force_allow or []):
            return True
        # Hide tags that are not allowed to be shown
        if check_permissions_to_show:
            has_permission_to_show = tag.get('has_permission_to_show', lambda r: True)(request)
            if has_permission_to_show != True:
                notAllowedReason(tag_name, tag, 'permission', has_permission_to_show)
                return False
        # Hidden by user
        if check_hidden_by_user:
            if request.user.is_authenticated():
                if request.user.preferences.hidden_tags:
                    if request.user.preferences.hidden_tags.get(tag_name, False):
                        notAllowedReason(tag_name, tag, 'user', _CHOOSE_HIDDEN_TAGS_MESSAGE)
                        return False
                else: # If the user didn't set their preferences, use default hidden tags
                    if tag_name in ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT:
                        notAllowedReason(tag_name, tag, 'user', _CHOOSE_HIDDEN_TAGS_MESSAGE)
                        return False
            else:
                if tag_name in ACTIVITIES_TAGS_HIDDEN_BY_DEFAULT:
                    notAllowedReason(tag_name, tag, 'user', _CHOOSE_HIDDEN_TAGS_MESSAGE)
                    return False
        # Hide tags that will happen in the future
        if tag_statuses[tag_name] == 'future':
            notAllowedReason(tag_name, tag, 'future')
            return False
        # When creating:
        if is_creating:
            # Don't allow tags that are not current
            if tag_statuses[tag_name] not in ['invalid', 'current']:
                notAllowedReason(tag_name, tag, 'past')
                return False
            # Don't allow tags that are not allowed to be added
            if not tag.get('has_permission_to_add', lambda r: True)(request):
                notAllowedReason(tag_name, tag, 'permission')
                return False
        return True
    def getTag(tag_name, tag):
        translation = tag['translation']() if callable(tag['translation']) else tag['translation']
        if full_tags:
            new_tag = tag.copy()
            new_tag.update({
                'translation': translation,
                'status': tag_statuses[tag_name],
            })
            return new_tag
        return translation
    allowed_tags = [
        (tag_name, getTag(tag_name, tag)) for tag_name, tag in ACTIVITY_TAGS.items()
        if isTagAllowed(tag_name, tag)
    ]
    if as_dict:
        allowed_tags = OrderedDict(allowed_tags)
    if return_not_allowed and return_allowed:
        return allowed_tags, not_allowed_tags_and_reasons
    elif return_not_allowed:
        return not_allowed_tags_and_reasons
    elif return_allowed:
        return allowed_tags
    return None

def getForbiddenTags(request, *args, **kwargs):
    return getAllowedTags(request, *args, return_allowed=False, return_not_allowed=True, **kwargs)

def saveActivityCacheOwnerWithoutChangingModification(activity):
    Activity.objects.filter(id=activity.id).update(**{
        k:v for k, v in
        model_to_dict(activity).items()
        if k.startswith('_cache')
    })

def updateCachedActivities(user_id):
    activities = Activity.objects.filter(owner_id=user_id).select_related('owner', 'owner__preferences')
    for activity in activities:
        activity.force_cache_owner()

############################################################
# Notification

class Notification(MagiModel):
    collection_name = 'notification'

    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='notifications', db_index=True, on_delete=models.CASCADE)
    creation = models.DateTimeField(auto_now_add=True)

    MESSAGES = [
        ('like', {
            'format': _(u'{} liked your activity: {}.'),
            'title': _(u'When someone likes your activity.'),
            'open_sentence': lambda n: _('Open {thing}').format(thing=_('Activity')),
            'url': u'/activity/{}/{}/',
            'icon': 'heart',
        }),
        ('follow', {
            'format': _(u'{} just followed you.'),
            'title': _(u'When someone follows you.'),
            'open_sentence': lambda n: _('Open {thing}').format(thing=_('Profile')),
            'url': u'/user/{}/{}/',
            'icon': 'users',
        }),
        ('like-archive', {
            'format': _(u'{} liked your activity: {}.'),
            'title': _(u'When someone likes an activity you archived.'),
            'open_sentence': lambda n: _('Open {thing}').format(thing=_('Activity')),
            'url': u'/activity/{}/{}/',
            'icon': 'heart',
        }),
        ('private-message', {
            'format': _(u'You have a new private message from {}.'),
            'title': _(u'When someone sends you a private message.'),
            'open_sentence': lambda n: _('Open {thing}').format(thing=_('Private message')),
            'url': '/privatemessages/?to_user={}',
            'icon': 'contact',
        }),
    ]
    MESSAGES_DICT = dict(MESSAGES)
    MESSAGE_CHOICES = [(key, _message['title']) for key, _message in MESSAGES]
    MESSAGE_SOFT_CHOICES = True
    i_message = models.PositiveIntegerField('Notification type')

    c_message_data = models.TextField(blank=True, null=True)
    c_url_data = models.TextField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    image = models.ImageField(upload_to=uploadItem('notifications'), null=True, blank=True, max_length=1200)

    def message_value(self, key):
        """
        Get the dictionary value for this key, for the current notification message.
        """
        return self.MESSAGES_DICT.get(self.message, {}).get(key, u'')

    @property
    def english_message(self):
        return self.message_value('format').format(*self.message_data).replace('\n', '')

    @property
    def localized_message(self):
        return _(self.message_value('format')).format(*self.message_data).replace('\n', '')

    @property
    def website_url(self):
        return self.message_value('url').format(*(self.url_data if self.url_data else self.message_data))

    @property
    def full_website_url(self):
        return u'{}{}'.format(SITE_URL if SITE_URL.startswith('http') else 'http:' + SITE_URL,
                          self.website_url[1:])

    @property
    def url_open_sentence(self):
        return self.message_value('open_sentence')(self)

    @property
    def icon(self):
        return self.message_value('icon')

    def __unicode__(self):
        return self.localized_message

    class Meta:
        ordering = ['-creation', '-id']

############################################################
# Report

class Report(MagiModel):
    collection_name = property(lambda _s: 'suggestededit' if _s.is_suggestededit else 'report')

    is_suggestededit = models.BooleanField(default=False, db_index=True)
    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='reports', null=True, on_delete=models.CASCADE)
    reported_thing = models.CharField(max_length=300) # Collection name
    reported_thing_title = models.CharField(max_length=300) # Collection title in English
    reported_thing_id = models.PositiveIntegerField() # Pk
    reported_thing_owner_id = models.PositiveIntegerField(null=True)
    reason = models.TextField(_('Reason'))
    message = models.TextField(_('Message'))
    images = models.ManyToManyField(UserImage, related_name="report", verbose_name=_('Images'), blank=True)
    staff = models.ForeignKey(User, related_name='staff_reports', null=True, on_delete=models.SET_NULL)
    staff_message = models.TextField('Staff message', null=True)

    STATUS_CHOICES = [
        'Pending', # No staff took care of it
        'Deleted', # Staff decided to delete the thing
        'Edited', # Staff decided to edit the thing
        'Ignored', # Staff decided to ignore the report
    ]

    i_status = models.PositiveIntegerField('Status', choices=i_choices(STATUS_CHOICES), default=0)
    saved_data = models.TextField(null=True)

    @property # Required by magicircles since the magicollection uses types
    def type(self):
        try:
            return self.reported_thing_collection.model_name
        except AttributeError:
            return None

    @property
    def reported_thing_collection(self):
        return getMagiCollection(self.reported_thing)

    @property
    def reported_thing_item_url(self):
        return u'/{thing}/{id}/'.format(thing=self.reported_thing, id=self.reported_thing_id)

    @property
    def reported_thing_ajax_item_url(self):
        return u'/ajax/{thing}/{id}/'.format(thing=self.reported_thing, id=self.reported_thing_id)

    @property
    def reported_thing_open_sentence(self):
        return _('Open {thing}').format(thing=_(self.reported_thing_title))

    @property
    def reported_thing_plural_name(self):
        if not self._reported_thing_plural_name:
            self._reported_thing_plural_name = self.reported_thing_collection.plural_name
        return self._reported_thing_plural_name
    _reported_thing_plural_name = None

    @property
    def item_view_enabled(self):
        return self.reported_thing_collection.item_view.enabled

    @property
    def allow_edit(self):
        return self.reported_thing_collection.report_allow_edit

    @property
    def allow_delete(self):
        return self.reported_thing_collection.report_allow_delete

    @property
    def allow_ajax(self):
        return self.reported_thing_collection.item_view.ajax

    @property
    def edit_templates(self):
        return self.reported_thing_collection.report_edit_templates

    @property
    def delete_templates(self):
        return self.reported_thing_collection.report_delete_templates

    @property
    def edited_fields(self):
        return self.reported_thing_collection.get_suggest_edit_choices(getattr(self, 'request', None))

    def __unicode__(self):
        return u'{title} #{id}'.format(
            title=str(_(self.reported_thing_title)),
            id=self.reported_thing_id,
        )

    class Meta:
        ordering = ['i_status']

############################################################
# Badge

BADGE_IMAGE_TINYPNG_SETTINGS = {
    'resize': 'cover',
    'width': 300,
    'height': 300,
}

class DonationMonth(MagiModel):
    collection_name = 'donate'

    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='donation_month_created', on_delete=models.CASCADE)
    date = models.DateField(default=datetime.datetime.now)
    cost = models.FloatField(default=250)
    goal = DONATORS_GOAL
    donations = models.FloatField(default=0)
    image = models.ImageField(_('Image'), upload_to=uploadItem('badges'))

    tinypng_settings = {
        'image': BADGE_IMAGE_TINYPNG_SETTINGS,
    }

    @property
    def percent_to_goal(self):
        if not DONATORS_GOAL: return 0
        percent = (self.donations / DONATORS_GOAL) * 100
        if percent > 100:
            return 100
        return percent

    @property
    def percent_to_cost(self):
        percent = (self.donations / self.cost) * 100
        if percent > 100:
            return 100
        return percent

    @property
    def percent(self):
        return self.percent_to_goal if DONATORS_GOAL else self.percent_to_cost

    @property
    def percent_int(self):
        return int(self.percent)

    @property
    def reached_100_percent(self):
        return self.percent_int >= 100

    @property
    def badge_name(self):
        return _(u'{month} Donator').format(
            month=date_format(self.date, format='YEAR_MONTH_FORMAT', use_l10n=True),
        )

    @property
    def open_badge_sentence(self):
        return _('Open {thing}').format(thing=str(_('Badge')).lower())

    @property
    def badge_sentence(self):
        return _(u'This is {month}\'s badge. It\'s limited to this month only, and only our donators can get it. It\'s not too late! If you donate now, it will appear on your profile.').format(
            month=_(self.date.strftime('%B')),
        )

    def __unicode__(self):
        return str(self.date)

    class Meta:
        ordering = ['-date']

class Badge(MagiModel):
    collection_name = 'badge'

    date = models.DateField(default=datetime.datetime.now)
    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='badges_created', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='badges', db_index=True, on_delete=models.CASCADE)
    donation_month = models.ForeignKey(DonationMonth, related_name='badges', null=True, on_delete=models.CASCADE)
    name = models.CharField(_('Title'), max_length=50, null=True)

    m_description = models.TextField(_('Description'), null=True)
    _cache_description = models.TextField(null=True)

    image = models.ImageField(_('Image'), upload_to=uploadItem('badges'))
    url = models.CharField(max_length=200, null=True)
    show_on_top_profile = models.BooleanField(default=False)
    show_on_profile = models.BooleanField(default=False)

    RANK_BRONZE = 1
    RANK_SILVER = 2
    RANK_GOLD = 3

    RANK_CHOICES = (
        (RANK_BRONZE, _('Bronze')),
        (RANK_SILVER, _('Silver')),
        (RANK_GOLD, _('Gold')),
    )
    RANK_CHOICES_DICT = dict(RANK_CHOICES)

    rank = models.PositiveIntegerField(null=True, blank=True, choices=RANK_CHOICES, help_text='Top 3 of this specific badge.')

    @property
    def t_rank(self):
        return self.RANK_CHOICES_DICT[self.rank]

    @property
    def rank_image_url(self):
        return staticImageURL(u'medal{}'.format(self.rank), folder='badges', extension='png')

    tinypng_settings = {
        'image': BADGE_IMAGE_TINYPNG_SETTINGS,
    }

    @property
    def type(self):
        return 'donator' if self.donation_month else 'exclusive'

    @property
    def donation_source(self):
        if self.type == 'donator':
            return self.m_description.split(' ')[0]
        return None

    @property
    def translated_name(self):
        if self.donation_month_id:
            return _(u'{month} Donator').format(month=date_format(self.date, format='YEAR_MONTH_FORMAT', use_l10n=True))
        return self.name

    @property
    def translated_description(self):
        if self.donation_month_id:
            return _('{donation_platform} supporter of {site_name} who donated to help cover the server costs').format(
                donation_platform=self.donation_source,
                site_name=SITE_NAME_PER_LANGUAGE.get(get_language(), SITE_NAME),
            )
        return self.description

    def __unicode__(self):
        return self.translated_name

    class Meta:
        ordering = ['-date']

############################################################
# Prize

class Prize(MagiModel):
    collection_name = 'prize'

    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='added_prizes', on_delete=models.CASCADE)
    name = models.CharField('Prize name', max_length=100)
    image = models.ImageField('Prize image', upload_to=uploadItem('prize'))
    image2 = models.ImageField('2nd image', upload_to=uploadItem('prize'), null=True, blank=True)
    image3 = models.ImageField('3rd image', upload_to=uploadItem('prize'), null=True, blank=True)
    image4 = models.ImageField('4th image', upload_to=uploadItem('prize'), null=True, blank=True)
    value = models.DecimalField('Value', null=True, help_text='in USD', max_digits=6, decimal_places=2)
    display_value = property(lambda _s: u'US ${}'.format(_s.value))

    CHARACTER_CHOICES = getCharactersChoices()
    CHARACTER_WITHOUT_I_CHOICES = True
    CHARACTER_SOFT_CHOICES = True
    i_character = models.CharField('Character', null=True, max_length=200)
    character_name = property(lambda _s: getCharacterNameFromPk(_s.i_character))
    t_character = character_name
    character_image = property(lambda _s: getCharacterImageFromPk(_s.i_character))
    character_url = property(lambda _s: getCharacterURLFromPk(_s.i_character))

    m_details = models.TextField('Details', null=True)

    giveaway_url = models.CharField('Giveaway URL', null=True, max_length=100, help_text='If you specify a giveaway URL, the prize will be considered unavailable for future giveaways')

    @property
    def top_html_list(self):
        if len(self.images_urls) > 1:
            return u"""
<div class="row">
  {images}
</div>
""".format(images=u''.join([
    u'<div class="col-md-6"><img src="{image}" class="img-responsive" alt="{item}"></div>'.format(
        image=image, item=self,
    ) for image in self.images_urls ]))
        return u'<img src="{image}" class="img-responsive" alt="{item}">'.format(
            image=self.images_urls[0], item=self)

    @property
    def display_name_in_list(self):
        return mark_safe(u"""
<small class="text-muted">{character_name}&nbsp;&nbsp;&nbsp;&nbsp;[#{id}]</small>
<br>{item}""".format(
    character_name=self.character_name or '', item=self, id=self.id))

    @property
    def images_urls(self):
        return [ i for i in [self.image_url, self.image2_url, self.image3_url, self.image4_url] if i ]

    def __unicode__(self):
        return self.name

############################################################
# Private message

class PrivateMessage(MagiModel):
    collection_name = 'privatemessage'

    owner = models.ForeignKey(User, verbose_name=_('User'), related_name='sent_messages', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    creation = models.DateTimeField(auto_now_add=True)
    message = models.TextField(_('Message'), max_length=1500)
    seen = models.BooleanField(default=False)

    PREVIEW_MAX_LENGTH = 100

    @property
    def message_preview(self):
        lines = self.message.split('\n')
        message = lines[0]
        if len(message) > self.PREVIEW_MAX_LENGTH:
            message = u' '.join(message[:self.PREVIEW_MAX_LENGTH+1].split(' ')[0:-1]) + u'...'
        elif len(lines) > 1:
            message += u'...'
        return message

    def __unicode__(self):
        return self.message

############################################################
# Callbacks to call on UserPreferences or User edited
# If you call these you should also call ON_USER_EDITED and ON_PREFERENCES_EDITED from settings.

def onUserEdited(user):
    updateCachedActivities(user.id)
    if issubclass(ACCOUNT_MODEL, CacheOwner):
        ACCOUNT_MODEL.objects.filter(owner=user).update(_cache_owner_last_update=None)

def onPreferencesEdited(user):
    if issubclass(ACCOUNT_MODEL, CacheOwner):
        ACCOUNT_MODEL.objects.filter(owner=user).update(_cache_owner_last_update=None)
