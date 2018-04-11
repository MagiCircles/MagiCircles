import hashlib, urllib, datetime, os
from collections import OrderedDict
from django.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.utils.translation import ugettext_lazy as _, string_concat
from django.utils import timezone
from django.utils.formats import dateformat
from django.forms.models import model_to_dict
from django.conf import settings as django_settings
from magi.utils import AttrDict, randomString, getMagiCollection, uploadToRandom, uploadItem, linkToImageURL
from magi.settings import ACCOUNT_MODEL, GAME_NAME, COLOR, SITE_STATIC_URL, DONATORS_STATUS_CHOICES, USER_COLORS, FAVORITE_CHARACTERS, SITE_URL, SITE_NAME, ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT, ACTIVITY_TAGS, GROUPS
from magi.item_model import MagiModel, BaseMagiModel, get_image_url, i_choices, addMagiModelProperties
from magi.abstract_models import CacheOwner

Account = ACCOUNT_MODEL

############################################################
# Utils

def avatar(user, size=200):
    """
    Preferences in user objects must always be prefetched
    """
    default = u'{}static/img/avatar.png'.format(SITE_STATIC_URL if SITE_STATIC_URL.startswith('http') else ('http:' + SITE_STATIC_URL if SITE_STATIC_URL.startswith('//') else 'http://' + SITE_STATIC_URL))
    if user.preferences.twitter:
        default = u'{}twitter_avatar/{}/'.format(SITE_URL if SITE_URL.startswith('http') else 'http:' + SITE_URL, user.preferences.twitter)
    return ("http://www.gravatar.com/avatar/"
            + hashlib.md5(user.email.lower()).hexdigest()
            + "?" + urllib.urlencode({'d': default, 's': str(size)}))

############################################################
# Add MagiModel properties to User objects

addMagiModelProperties(User, 'user')
User.image_url = property(avatar)
User.http_image_url = property(avatar)
User.owner_id = property(lambda u: u.id)
User.owner = property(lambda u: u)

############################################################
# Utility Models

class UserImage(BaseMagiModel):
    image = models.ImageField(upload_to=uploadToRandom('user_images/'))

    def __unicode__(self):
        return unicode(self.image_url)

############################################################
# User preferences

class UserPreferences(BaseMagiModel):
    user = models.OneToOneField(User, related_name='preferences', on_delete=models.CASCADE)

    LANGUAGE_CHOICES = django_settings.LANGUAGES
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = django_settings.LANGUAGES
    i_language = models.CharField(_('Language'), max_length=10)

    description = models.TextField(_('Description'), null=True, help_text=_('Write whatever you want. You can add formatting and links using Markdown.'), blank=True)
    favorite_character1 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('1st')), null=True, max_length=200)
    favorite_character2 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('2nd')), null=True, max_length=200)
    favorite_character3 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('3rd')), null=True, max_length=200)
    color = models.CharField(_('Color'), max_length=100, null=True, blank=True)
    birthdate = models.DateField(_('Birthdate'), blank=True, null=True)
    default_tab = models.CharField(_('Default tab'), max_length=100, null=True)
    location = models.CharField(_('Location'), max_length=200, null=True, blank=True, help_text=string_concat(_('The city you live in.'), ' ', _('It might take up to 24 hours to update your location on the map.')))
    location_changed = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    following = models.ManyToManyField(User, related_name='followers')

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

    STATUS_COLOR_STRINGS = {
        'SUPPORTER': _('blue'),
        'LOVER':  _('pink'),
        'AMBASSADOR':  _('shiny Silver'),
        'PRODUCER':  _('shiny Gold'),
        'DEVOTEE':  _('shiny Gold'),
    }

    STATUS_WITHOUT_I_CHOICES = True
    STATUS_SOFT_CHOICES = STATUS_CHOICES
    i_status = models.CharField('Status', max_length=12, null=True)
    @property
    def status_color(self):
        return self.STATUS_COLORS[self.i_status] if self.i_status else None
    @property
    def status_color_string(self):
        return self.STATUS_COLOR_STRINGS[self.i_status] if self.i_status else None

    donation_link = models.CharField(max_length=200, null=True, blank=True)
    donation_link_title = models.CharField(max_length=100, null=True, blank=True)
    view_activities_language_only = models.BooleanField(_('View activities in your language only?'), default=ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT)
    email_notifications_turned_off_string = models.CharField(max_length=15, null=True)
    unread_notifications = models.PositiveIntegerField(default=0)
    invalid_email = models.BooleanField(default=False)

    GROUPS_CHOICES = [(_k, _v['translation']) for _k, _v in GROUPS]
    GROUPS = OrderedDict(GROUPS)
    c_groups = models.TextField(_('Roles'), blank=True, null=True)

    @property
    def groups_and_details(self):
        return {
            group: self.GROUPS[group]
            for group in self.groups
        }

    d_extra = models.TextField(blank=True, null=True)

    def localized_favorite_character(self, number):
        if getattr(self, 'favorite_character{}'.format(number)) and FAVORITE_CHARACTERS:
            try:
                return (_(localized) for (name, localized, __) in FAVORITE_CHARACTERS if unicode(name) == getattr(self, 'favorite_character{}'.format(number))).next()
            except: pass
        return ''
    @property
    def localized_favorite_character1(self): return self.localized_favorite_character(1)
    @property
    def localized_favorite_character2(self): return self.localized_favorite_character(2)
    @property
    def localized_favorite_character3(self): return self.localized_favorite_character(3)

    def favorite_character_image(self, number):
        if getattr(self, 'favorite_character{}'.format(number)) and FAVORITE_CHARACTERS:
            try:
                imagePath = (image for (name, __, image) in FAVORITE_CHARACTERS if unicode(name) == getattr(self, 'favorite_character{}'.format(number))).next()
            except StopIteration:
                return None
            if '//' in imagePath:
                return imagePath
            return get_image_url(imagePath)
        return None

    @property
    def favorite_character1_image(self): return self.favorite_character_image(1)
    @property
    def favorite_character2_image(self): return self.favorite_character_image(2)
    @property
    def favorite_character3_image(self): return self.favorite_character_image(3)

    @classmethod
    def get_localized_color(self, color):
        if color and USER_COLORS:
            try:
                return (_(localized) for (name, localized, __, __) in USER_COLORS if unicode(name) == color).next()
            except: pass
        return ''
    @property
    def localized_color(self):
        return type(self).get_localized_color(self.color)

    @classmethod
    def get_hex_color(self, color):
        if color and USER_COLORS:
            try:
                return (hex for (name, _, _, hex) in USER_COLORS if unicode(name) == color).next()
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
                return (css_color for (name, _, css_color, _) in USER_COLORS if unicode(name) == color).next()
            except: pass
        return 'main'
    @property
    def css_color(self):
        return type(self).get_css_color(self.color)

    @classmethod
    def get_age(self, birthdate):
        if not birthdate:
            return None
        today = datetime.date.today()
        return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    @property
    def age(self):
        return type(self).get_age(self.birthdate)

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

    # Cache twitter
    _cache_twitter = models.CharField(max_length=32, null=True, blank=True) # changed when links are modified

    @property
    def twitter(self):
        return self._cache_twitter

    class Meta:
        verbose_name_plural = "list of userpreferences"

############################################################
# User links

class UserLink(BaseMagiModel):
    alphanumeric = validators.RegexValidator(r'^[0-9a-zA-Z-_\. ]*$', 'Only alphanumeric and - _ characters are allowed.')
    owner = models.ForeignKey(User, related_name='links')
    value = models.CharField(_('Username/ID'), max_length=64, help_text=_('Write your username only, no URL.'), validators=[alphanumeric])

    TYPE_CHOICES = (
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('reddit', 'Reddit'),
        ('schoolidolu', 'School Idol Tomodachi'),
        ('stardustrun', 'Stardust Run'),
        ('frgl', 'fr.gl'),
        ('line', 'LINE Messenger'),
        ('tumblr', 'Tumblr'),
        ('twitch', 'Twitch'),
        ('steam', 'Steam'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('github', 'GitHub'),
    )

    TYPE_WITHOUT_I_CHOICES = True
    i_type = models.CharField(_('Platform'), max_length=20, choices=TYPE_CHOICES)

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
        'schoolidolu': u'http://schoolido.lu/user/{}/',
        'frgl': u'http://fr.gl/user/{}/',
        'stardustrun': u'http://stardust.run/user/{}/',
        'line': u'http://line.me/#{}',
        'tumblr': u'http://{}.tumblr.com/',
        'twitch': u'http://twitch.tv/{}',
        'steam': u'http://steamcommunity.com/id/{}',
        'instagram': u'https://instagram.com/{}/',
        'youtube': u'https://www.youtube.com/{}',
        'github': u'https://github.com/{}',
    }

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

    owner = models.ForeignKey(User, related_name='added_configurations')
    key = models.CharField(max_length=100)
    verbose_key = models.CharField('Name', max_length=100)
    value = models.TextField('Value', null=True)

    LANGUAGE_CHOICES = django_settings.LANGUAGES
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = LANGUAGE_CHOICES
    i_language = models.CharField(_('Language'), max_length=10, null=True)

    is_long = models.BooleanField(default=False)
    is_markdown = models.BooleanField(default=False)
    is_boolean = models.BooleanField(default=False)

    # Owner is always pre-selected
    @property
    def cached_owner(self):
        self.owner.unicode = unicode(self.owner)
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

############################################################
# Activity

class Activity(MagiModel):
    collection_name = 'activity'

    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='activities')
    message = models.TextField(_('Message'))
    likes = models.ManyToManyField(User, related_name="liked_activities")

    LANGUAGE_CHOICES = django_settings.LANGUAGES
    LANGUAGE_WITHOUT_I_CHOICES = True
    LANGUAGE_SOFT_CHOICES = LANGUAGE_CHOICES
    i_language = models.CharField(_('Language'), max_length=10)

    TAGS_CHOICES = ACTIVITY_TAGS if ACTIVITY_TAGS else []
    c_tags = models.TextField(_('Tags'), blank=True, null=True)

    image = models.ImageField(_('Image'), upload_to=uploadToRandom('activities/'), null=True, blank=True, help_text=_('Only post official artworks, artworks you own, or fan artworks that are approved by the artist and credited.'))

    tinypng_settings = {
        'image': {
            'resize': 'fit',
        }
    }

    # Cache
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
                'status': dict(UserPreferences.STATUS_CHOICES)[self._cache_owner_preferences_i_status] if self._cache_owner_preferences_i_status else None,
                'twitter': self._cache_owner_preferences_twitter,
            }),
        })
        return cached_owner

    @property
    def shareSentence(self):
        return _(u'Check out {username}\'s activity on {site}: {activity}').format(
            username=self.cached_owner.username,
            site=SITE_NAME,
            activity=self.summarize(40),
        )

    def summarize(self, length=100):
        """
        Return the first {length} characters without cutting words
        """
        if len(self.message) <= length:
            return self.message
        return u' '.join(self.message[:length+1].split(' ')[0:-1]) + u'...'

    def __unicode__(self):
        return self.summarize()

    class Meta:
        verbose_name_plural = "activities"

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

    owner = models.ForeignKey(User, related_name='notifications', db_index=True)
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
    ]
    MESSAGES_DICT = dict(MESSAGES)
    MESSAGE_CHOICES = [(key, _message['title']) for key, _message in MESSAGES]
    i_message = models.PositiveIntegerField('Notification type', choices=i_choices(MESSAGE_CHOICES))

    c_message_data = models.TextField(blank=True, null=True)
    c_url_data = models.TextField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    image = models.ImageField(upload_to=uploadItem('notifications/'), null=True, blank=True)

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

############################################################
# Report

class Report(MagiModel):
    collection_name = 'report'

    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='reports', null=True)
    reported_thing = models.CharField(max_length=300)
    reported_thing_title = models.CharField(max_length=300)
    reported_thing_id = models.PositiveIntegerField()
    reason = models.TextField(_('Reason'))
    message = models.TextField(_('Message'))
    images = models.ManyToManyField(UserImage, related_name="report", verbose_name=_('Images'))
    staff = models.ForeignKey(User, related_name='staff_reports', null=True, on_delete=models.SET_NULL)
    staff_message = models.TextField(null=True)

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
        return self.reported_thing

    @property
    def reported_thing_collection(self):
        return getMagiCollection(self.reported_thing)

    @property
    def reported_thing_open_sentence(self):
        return _('Open {thing}').format(thing=_(self.reported_thing_title))

    @property
    def reported_thing_plural_name(self):
        if not self._reported_thing_plural_name:
            self._reported_thing_plural_name = getMagiCollection(self.reported_thing).plural_name
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
    def edit_templates(self):
        return self.reported_thing_collection.report_edit_templates

    @property
    def delete_templates(self):
        return self.reported_thing_collection.report_delete_templates

    def __unicode__(self):
        return u'{title} #{id}'.format(
            title=unicode(_(self.reported_thing_title)),
            id=self.reported_thing_id,
        )

############################################################
# Badge

BADGE_IMAGE_TINYPNG_SETTINGS = {
    'resize': 'cover',
    'width': 300,
    'height': 300,
}

class DonationMonth(MagiModel):
    collection_name = 'donate'

    owner = models.ForeignKey(User, related_name='donation_month_created')
    date = models.DateField(default=datetime.datetime.now)
    cost = models.FloatField(default=250)
    donations = models.FloatField(default=0)
    image = models.ImageField(_('Image'), upload_to=uploadItem('badges/'))

    tinypng_settings = {
        'image': BADGE_IMAGE_TINYPNG_SETTINGS,
    }

    @property
    def percent(self):
        percent = (self.donations / self.cost) * 100
        if percent > 100:
            return 100
        return percent

    @property
    def percent_int(self):
        return int(self.percent)

    def __unicode__(self):
        return unicode(self.date)

class Badge(MagiModel):
    collection_name = 'badge'

    date = models.DateField(default=datetime.datetime.now)
    owner = models.ForeignKey(User, related_name='badges_created')
    user = models.ForeignKey(User, related_name='badges', db_index=True)
    donation_month = models.ForeignKey(DonationMonth, related_name='badges', null=True)
    name = models.CharField(max_length=50, null=True)
    description = models.CharField(max_length=300)
    image = models.ImageField(_('Image'), upload_to=uploadItem('badges/'))
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

    rank = models.PositiveIntegerField(null=True, blank=True, choices=RANK_CHOICES, help_text='Top 3 of this specific badge.')

    tinypng_settings = {
        'image': BADGE_IMAGE_TINYPNG_SETTINGS,
    }

    @property
    def type(self):
        return 'donator' if self.donation_month else 'exclusive'

    @property
    def donation_source(self):
        if self.type == 'donator':
            return self.description.split(' ')[0]
        return None

    @property
    def translated_name(self):
        if self.donation_month_id:
            return _(u'{month} Donator').format(month=dateformat.format(self.date, "F Y"))
        return self.name

    @property
    def translated_description(self):
        if self.donation_month_id:
            return _('{donation_platform} supporter of {site_name} who donated to help cover the server costs').format(
                donation_platform=self.donation_source,
                site_name=SITE_NAME,
            )
        return self.description

    def __unicode__(self):
        return self.translated_name

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
