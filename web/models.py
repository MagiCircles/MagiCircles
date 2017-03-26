import hashlib, urllib, datetime, os
from django.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.utils.translation import ugettext_lazy as _, string_concat
from django.utils import timezone
from django.utils.formats import dateformat
from django.forms.models import model_to_dict
from django.conf import settings as django_settings
from web.utils import AttrDict, join_data, split_data, randomString, getMagiCollection, uploadToRandom, uploadItem, linkToImageURL
from web.settings import ACCOUNT_MODEL, GAME_NAME, COLOR, SITE_STATIC_URL, DONATORS_STATUS_CHOICES, USER_COLORS, FAVORITE_CHARACTERS, SITE_URL, SITE_NAME, ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT
from web.item_model import *
from web.model_choices import *

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
# Add ItemModel properties to User objects

addItemModelProperties(User, 'user')
User.image_url = property(avatar)
User.http_image_ur = property(avatar)
User.owner_id = property(lambda u: u.id)
User.owner = property(lambda u: u)

############################################################
# Utility Models

class UserImage(ItemModel):
    collection_name = 'userimages' # Doesn't exist in default_settings.py
    image = models.ImageField(upload_to=uploadToRandom('user_images/'))

    def __unicode__(self):
        return unicode(self.image)

############################################################
# User preferences

class UserPreferences(models.Model):
    user = models.OneToOneField(User, related_name='preferences', on_delete=models.CASCADE)
    language = models.CharField(_('Language'), max_length=10, choices=django_settings.LANGUAGES)
    @property
    def localized_language(self):
        return LANGUAGES_DICT[self.language]
    description = models.TextField(_('Description'), null=True, help_text=_('Write whatever you want. You can add formatting and links using Markdown.'), blank=True)
    favorite_character1 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('1st')), null=True, max_length=200)
    favorite_character2 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('2nd')), null=True, max_length=200)
    favorite_character3 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('3rd')), null=True, max_length=200)
    color = models.CharField(_('Color'), max_length=100, null=True, blank=True)
    birthdate = models.DateField(_('Birthdate'), blank=True, null=True)
    location = models.CharField(_('Location'), max_length=200, null=True, blank=True, help_text=string_concat(_('The city you live in.'), ' ', _('It might take up to 24 hours to update your location on the map.')))
    location_changed = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    following = models.ManyToManyField(User, related_name='followers')
    i_status = models.CharField(choices=STATUS_CHOICES, max_length=12, null=True)
    @property
    def status(self):
        return STATUS_CHOICES_DICT[self.i_status] if self.i_status else None
    @property
    def status_color(self):
        return STATUS_COLORS[self.i_status] if self.i_status else None
    @property
    def status_color_string(self):
        return STATUS_COLOR_STRINGS[self.i_status] if self.i_status else None
    donation_link = models.CharField(max_length=200, null=True, blank=True)
    donation_link_title = models.CharField(max_length=100, null=True, blank=True)
    view_activities_language_only = models.BooleanField(_('View activities in your language only?'), default=ONLY_SHOW_SAME_LANGUAGE_ACTIVITY_BY_DEFAULT)
    email_notifications_turned_off_string = models.CharField(max_length=15, null=True)
    unread_notifications = models.PositiveIntegerField(default=0)
    invalid_email = models.BooleanField(default=False)

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

    @property
    def localized_color(self):
        if self.color and USER_COLORS:
            try:
                return (_(localized) for (name, localized, __, __) in USER_COLORS if unicode(name) == self.color).next()
            except: pass
        return ''

    @property
    def hex_color(self):
        if self.color and USER_COLORS:
            try:
                return (hex for (name, _, _, hex) in USER_COLORS if unicode(name) == self.color).next()
            except: pass
        return COLOR

    @property
    def css_color(self):
        if self.color and USER_COLORS:
            try:
                return (css_color for (name, _, css_color, _) in USER_COLORS if unicode(name) == self.color).next()
            except: pass
        return 'main'

    @property
    def age(self):
        if not self.birthdate:
            return None
        today = datetime.date.today()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))

    @property
    def email_notifications_turned_off(self):
        if not self.email_notifications_turned_off_string:
            return []
        return [int(t) for t in self.email_notifications_turned_off_string.split(',')]

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

    # Cache
    _cache_twitter = models.CharField(max_length=32, null=True, blank=True) # changed when links are modified

    @property
    def twitter(self):
        return self._cache_twitter

    class Meta:
        verbose_name_plural = "list of userpreferences"

############################################################
# User links

class UserLink(models.Model):
    alphanumeric = validators.RegexValidator(r'^[0-9a-zA-Z-_\. ]*$', 'Only alphanumeric and - _ characters are allowed.')
    owner = models.ForeignKey(User, related_name='links')
    i_type = models.CharField(_('Platform'), max_length=20, choices=LINK_CHOICES)
    @property
    def type(self):
        return LINK_CHOICES_DICT.get(self.i_type, self.i_type)
    value = models.CharField(_('Username/ID'), max_length=64, help_text=_('Write your username only, no URL.'), validators=[alphanumeric])
    i_relevance = models.PositiveIntegerField(_(u'How often do you tweet/stream/post about {}?').format(GAME_NAME), choices=LINK_RELEVANCE_CHOICES, null=True, blank=True)
    @property
    def relevance(self):
        return LINK_RELEVANCE_CHOICES_DICT.get(self.i_relevance, None) if self.i_relevance else None

    @property
    def url(self):
        if self.type in LINK_URLS:
            return LINK_URLS[self.type].format(self.value)
        return '#'

    @property
    def image_url(self):
        if self.i_type in LINK_URLS:
            return linkToImageURL(self)
        return None

############################################################
# Activity

class Activity(ItemModel):
    collection_name = 'activity'

    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='activities')
    message = models.TextField(_('Message'))
    likes = models.ManyToManyField(User, related_name="liked_activities")
    language = models.CharField(_('Language'), max_length=4, choices=django_settings.LANGUAGES)
    @property
    def localized_language(self):
        return LANGUAGES_DICT[self.language]
    tags_string = models.TextField(blank=True, null=True)
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
    _cache_owner_preferences_i_status = models.CharField(choices=STATUS_CHOICES, max_length=12, null=True)
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
                'status': STATUS_CHOICES_DICT[self._cache_owner_preferences_i_status] if self._cache_owner_preferences_i_status else None,
                'twitter': self._cache_owner_preferences_twitter,
            }),
        })
        return cached_owner

    @property
    def tags(self):
        return split_data(self.tags_string)

    @property
    def localized_tags(self):
        return [(tag, ACTIVITY_TAGS_DICT[tag]) for tag in self.tags]

    def add_tags(self, new_tags):
        self.tags_string = join_data(*(self.tags + [tag for tag in new_tags if tag not in tags]))

    def remove_tags(self, tags_to_remove):
        self.tags_string = join_data(*[tag for tag in self.tags if tag not in tags_to_remove])

    def save_tags(self, tags):
        """
        Will completely replace any existing list of tags.
        """
        self.tags_string = join_data(*tags)

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

class Notification(ItemModel):
    collection_name = 'notification'

    owner = models.ForeignKey(User, related_name='notifications', db_index=True)
    creation = models.DateTimeField(auto_now_add=True)
    message = models.PositiveIntegerField(choices=NOTIFICATION_CHOICES)
    message_data = models.TextField(blank=True, null=True)
    url_data = models.TextField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    image = models.ImageField(upload_to=uploadItem('notifications/'), null=True, blank=True)

    @property
    def english_message(self):
        data = split_data(self.message_data)
        return NOTIFICATION_DICT[self.message].format(*data).replace('\n', '')

    @property
    def localized_message(self):
        data = split_data(self.message_data)
        return _(NOTIFICATION_DICT[self.message]).format(*data).replace('\n', '')

    @property
    def website_url(self):
        data = split_data(self.url_data if self.url_data else self.message_data)
        return NOTIFICATION_URLS[self.message].format(*data)

    @property
    def full_website_url(self):
        return u'{}{}'.format(SITE_URL if SITE_URL.startswith('http') else 'http:' + SITE_URL,
                          self.website_url[1:])

    @property
    def url_open_sentence(self):
        return NOTIFICATION_OPEN_SENTENCES[self.message](self)

    @property
    def icon(self):
        return NOTIFICATION_ICONS[self.message]

    def __unicode__(self):
        return self.localized_message

############################################################
# Report

class Report(ItemModel):
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
    i_status = models.PositiveIntegerField(choices=REPORT_STATUSES, default=0)
    @property
    def status(self): return REPORT_STATUSES_DICT[self.i_status]
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

class DonationMonth(ItemModel):
    collection_name = 'donate'

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

class Badge(ItemModel):
    collection_name = 'badge'

    date = models.DateField(default=datetime.datetime.now)
    owner = models.ForeignKey(User, related_name='badges_created')
    user = models.ForeignKey(User, related_name='badges')
    donation_month = models.ForeignKey(DonationMonth, related_name='badges', null=True)
    name = models.CharField(max_length=50, null=True)
    description = models.CharField(max_length=300)
    image = models.ImageField(_('Image'), upload_to=uploadItem('badges/'))
    url = models.CharField(max_length=200, null=True)
    show_on_top_profile = models.BooleanField(default=False)
    show_on_profile = models.BooleanField(default=False)
    rank = models.PositiveIntegerField(null=True, blank=True, choices=BADGE_RANK_CHOICES, help_text='Top 3 of this specific badge.')

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
