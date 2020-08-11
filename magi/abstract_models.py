import datetime
from collections import OrderedDict
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _, string_concat
from django.db import models
from django.conf import settings as django_settings
from django.core.validators import RegexValidator
from django.utils import timezone
from magi.django_translated import t
from magi.item_model import (
    MagiModel,
    get_image_url_from_path,
    i_choices,
    getInfoFromChoices,
    ALL_ALT_LANGUAGES,
)
from magi.utils import (
    AttrDict,
    PastOnlyValidator,
    uploadItem,
    uploadThumb,
    uploadTiny,
    modelHasField,
    filterRealAccounts,
    staticImageURL,
    getEventStatus,
)
from magi.versions_utils import (
    getRelevantVersion,
    getFieldForRelevantVersion,
    getTranslatedValueForRelevantVersion,
    getFieldNameForVersion,
    getFieldForVersion,
    getLanguagesForVersion,
    getTranslatedValuesForVersion,
    getRelevantTranslatedValueForVersion,
)
from magi.default_settings import RAW_CONTEXT

############################################################
# AccountAsOwnerModel

class AccountAsOwnerModel(MagiModel):
    """
    Will provide a cache when item doesn't have an owner but has an account.
    You need to provide the account field in your model:
    account = models.ForeignKey(Account, verbose_name=_('Account'))
    """
    fk_as_owner = 'account'

    # Cache account

    _cache_account_days = 200 # Change to a lower value if owner can change
    _cache_account_last_update = models.DateTimeField(null=True)
    _cache_j_account = models.TextField(null=True)

    @classmethod
    def cached_account_extra(self, d):
        d['owner']['pk'] = d['owner']['id']
        d['owner']['unicode'] = unicode(d['owner']['id'])
        d['item_url'] = u'/user/{}/#{}'.format(d['owner']['id'], d['id'])
        d['full_item_url'] = u'{}{}'.format(django_settings.SITE_URL, d['item_url'])
        d['http_item_url'] = u'http:' + d['full_item_url'] if 'http' not in d['full_item_url'] else d['full_item_url']
        d['owner'] = AttrDict(d['owner'])

    def to_cache_account(self):
        return {
            'id': self.account_id,
            'unicode': unicode(self.account),
            'owner': {
                'id': self.account.owner_id,
            },
        }

    @property
    def owner(self):
        return self.cached_account.owner

    @property
    def owner_id(self):
        return self.cached_account.owner.id

    class Meta:
        abstract = True

############################################################
# CacheAccount

class CacheOwner(MagiModel):
    """
    Will provide a cache with basic owner details
    """
    _cache_owner_days = 200
    _cache_owner_last_update = models.DateTimeField(null=True)
    _cache_owner_username = models.CharField(max_length=32, null=True)
    _cache_owner_email = models.EmailField(blank=True)
    _cache_owner_preferences_i_status = models.CharField(max_length=12, null=True)
    _cache_owner_preferences_twitter = models.CharField(max_length=32, null=True, blank=True)
    _cache_owner_color = models.CharField(max_length=100, null=True, blank=True)

    def update_cache_owner(self):
        """
        Recommended to use select_related('owner', 'owner__preferences') when calling this method
        """
        self._cache_owner_last_update = timezone.now()
        self._cache_owner_username = self.real_owner.username
        self._cache_owner_email = self.real_owner.email
        self._cache_owner_preferences_i_status = self.real_owner.preferences.i_status
        self._cache_owner_preferences_twitter = self.real_owner.preferences.twitter
        self._cache_owner_color = self.real_owner.preferences.color

    def force_cache_owner(self):
        self.update_cache_owner()
        self.save()

    @property
    def cached_owner(self):
        if not self._cache_owner_last_update or self._cache_owner_last_update < timezone.now() - datetime.timedelta(days=self._cache_owner_days):
            self.force_cache_owner()
        preferences_model = RAW_CONTEXT.get('preferences_model')
        full_item_url = '{}user/{}/{}/'.format(django_settings.SITE_URL, self.owner_id, self._cache_owner_username)
        http_item_url = u'http:' + full_item_url if 'http' not in full_item_url else full_item_url
        return AttrDict({
            'pk': self.owner_id,
            'id': self.owner_id,
            'username': self._cache_owner_username,
            'email': self._cache_owner_email,
            'item_url': '/user/{}/{}/'.format(self.owner_id, self._cache_owner_username),
            'ajax_item_url': '/ajax/user/{}/'.format(self.owner_id),
            'full_item_url': full_item_url,
            'http_item_url': http_item_url,
            'share_url': http_item_url,
            'preferences': AttrDict({
                'i_status': self._cache_owner_preferences_i_status,
                'status': self._cache_owner_preferences_i_status,
                'status_color': dict(preferences_model.STATUS_COLORS).get(self._cache_owner_preferences_i_status, None) if preferences_model and self._cache_owner_preferences_i_status else None,
                't_status': dict(preferences_model.STATUS_CHOICES)[self._cache_owner_preferences_i_status] if preferences_model and self._cache_owner_preferences_i_status else None,
                'is_premium': self._cache_owner_preferences_i_status and self._cache_owner_preferences_i_status != 'THANKS',
                'twitter': self._cache_owner_preferences_twitter,
                'color': self._cache_owner_color,
                'localized_color': preferences_model.get_localized_color(self._cache_owner_color) if preferences_model else None,
                'hex_color': preferences_model.get_hex_color(self._cache_owner_color) if preferences_model else None,
                'rgb_color': preferences_model.get_rgb_color(self._cache_owner_color) if preferences_model else None,
                'css_color': preferences_model.get_css_color(self._cache_owner_color) if preferences_model else None,
            }),
        })

    class Meta:
        abstract = True

############################################################
# BaseAccount

class BaseAccount(CacheOwner):
    collection_name = 'account'

    owner = models.ForeignKey(User, related_name='accounts')
    creation = models.DateTimeField(_('Join date'), auto_now_add=True)
    nickname = models.CharField(_('Nickname'), max_length=200, null=True, help_text=_('Give a nickname to your account to easily differentiate it from your other accounts when you\'re managing them.'))
    start_date = models.DateField(_('Start date'), null=True, validators=[PastOnlyValidator])
    level = models.PositiveIntegerField(_('Level'), null=True)

    default_tab = models.CharField(_('Default tab'), max_length=100, null=True)

    show_friend_id = True

    # Share URL

    def share_url(self):
        return u'{}#{}'.format(self.cached_owner.share_url, self.id)

    # Cache: leaderboard position

    _cache_leaderboards_days = 1
    _cache_leaderboards_last_update = models.DateTimeField(null=True)
    _cache_leaderboard = models.PositiveIntegerField(null=True)

    def cache_leaderboard_accounts(self):
        return filterRealAccounts(type(self).objects.all()).filter(
            level__gt=self.level)

    def to_cache_leaderboard(self):
        return self.cache_leaderboard_accounts().values('level').distinct().count() + 1

    def update_cache_leaderboards(self):
        self._cache_leaderboards_last_update = timezone.now()
        self._cache_leaderboard = self.to_cache_leaderboard()

    def force_cache_leaderboards(self):
        self.update_cache_leaderboards()
        self.save()

    @property
    def cached_leaderboard(self):
        if not self.level:
            return None
        if not self._cache_leaderboards_last_update or self._cache_leaderboards_last_update < timezone.now() - datetime.timedelta(days=self._cache_leaderboards_days):
            self.force_cache_leaderboards()
        return self._cache_leaderboard

    @property
    def leaderboard_image_url(self):
        return get_image_url_from_path(u'static/img/badges/medal{}.png'.format(4 - self.cached_leaderboard))

    def __unicode__(self):
        if self.id:
            return u'{}{}'.format(
                self.nickname if self.nickname else self.cached_owner.username,
                u' {}'.format(_(u'Level {level}').format(level=self.level)) if self.level else u'')
        return u'Level {}'.format(self.level) if self.level else u''

    class Meta:
        abstract = True


class MobileGameAccount(BaseAccount):

    # Friend ID

    friend_id = models.CharField(_('Friend ID'), null=True, max_length=100, validators=[
        RegexValidator(r'^[0-9 ]+$', t['Enter a number.']),
    ])
    show_friend_id = models.BooleanField(_('Should your friend ID be visible to other players?'), default=True)
    accept_friend_requests = models.NullBooleanField(_('Accept friend requests'), null=True)

    # How do you play?

    PLAY_WITH = OrderedDict([
        ('Thumbs', {
            'translation': _('Thumbs'),
            'icon': 'thumbs'
        }),
        ('Fingers', {
            'translation': _('All fingers'),
            'icon': 'fingers'
        }),
        ('Index', {
            'translation': _('Index fingers'),
            'icon': 'index'
        }),
        ('Hand', {
            'translation': _('One hand'),
            'icon': 'fingers'
        }),
        ('Other', {
            'translation': _('Other'),
            'icon': 'sausage'
        }),
    ])
    PLAY_WITH_CHOICES = [(name, info['translation']) for name, info in PLAY_WITH.items()]

    i_play_with = models.PositiveIntegerField(_('Play with'), choices=i_choices(PLAY_WITH_CHOICES), null=True)
    play_with_icon = property(getInfoFromChoices('play_with', PLAY_WITH, 'icon'))

    OSES = OrderedDict([
        ('android', 'Android'),
        ('ios', 'iOS'),
    ])
    OS_CHOICES = list(OSES.items())
    i_os = models.PositiveIntegerField(_('Operating System'), choices=i_choices(OS_CHOICES), null=True)

    device = models.CharField(
        _('Device'), max_length=150, null=True,
        help_text=_('The model of your device. Example: Nexus 5, iPhone 4, iPad 2, ...'),
    )

    # Verifications

    screenshot = models.ImageField(
        _('Screenshot'), help_text=_('In-game profile screenshot'),
        upload_to=uploadItem('account_screenshot'), null=True, blank=True)
    _thumbnail_screenshot = models.ImageField(null=True, upload_to=uploadThumb('account_screenshot'))
    level_on_screenshot_upload = models.PositiveIntegerField(null=True)
    is_hidden_from_leaderboard = models.BooleanField('Hide from leaderboard', default=False, db_index=True)
    is_playground = models.BooleanField(
        _('Playground'), default=False, db_index=True,
        help_text=_('Check this box if this account doesn\'t exist in the game.'),
    )

    class Meta:
        abstract = True

############################################################
# BaseEvent

class _BaseEvent(MagiModel):
    collection_name = 'event'

    owner = models.ForeignKey(User, related_name='added_%(class)ss')

    ############################################################
    # Name

    name = models.CharField(_('Title'), max_length=100, null=True)
    NAMES_CHOICES = ALL_ALT_LANGUAGES
    d_names = models.TextField(_('Title'), null=True)

    ############################################################
    # Description

    m_description = models.TextField(_('Description'), null=True)
    M_DESCRIPTIONS_CHOICES = ALL_ALT_LANGUAGES
    d_m_descriptions = models.TextField(_('Description'), null=True)
    _cache_description = models.TextField(null=True)

    def __unicode__(self):
        return unicode(self.t_name)

    class Meta(MagiModel.Meta):
        abstract = True

class BaseEvent(_BaseEvent):
    collection_name = 'event'

    image = models.ImageField(_('Image'), upload_to=uploadItem('event'), null=True)
    _original_image = models.ImageField(null=True, upload_to=uploadTiny('event'))

    start_date = models.DateTimeField(_('Beginning'), null=True)
    end_date = models.DateTimeField(_('End'), null=True)

    get_status = lambda _s: getEventStatus(_s.start_date, _s.end_date)
    status = property(get_status)

    class Meta(MagiModel.Meta):
        abstract = True

BASE_EVENT_FIELDS_PER_VERSION = OrderedDict([
    (u'{}image', lambda _version_name, _version: models.ImageField(
        string_concat(_version['translation'], ' - ', _('Image')),
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True,
    )),
    (u'_original_{}image', lambda _version_name, _version: models.ImageField(
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True,
    )),
    (u'{}start_date', lambda _version_name, _version: models.DateTimeField(
        string_concat(_version['translation'], ' - ', _('Beginning')), null=True,
    )),
    (u'{}end_date', lambda _version_name, _version: models.DateTimeField(
        string_concat(_version['translation'], ' - ', _('End')), null=True,
    )),
])

BASE_EVENT_UTILS_PER_VERSION = OrderedDict([
    (u'{}name', lambda _version_name, _version: property(lambda _s: _s.get_name_for_version(_version_name))),
    (u'{}status', lambda _version_name, _version: property(lambda _s: _s.get_status_for_version(_version_name))),
])

# todo: change plural title of event participations
# javascript for events stuff

def getBaseEventWithVersions(versions, defaults={}, fallbacks={}, extra_fields=None, extra_utils=None):
    """
    `versions` is an ordered dict with values being dicts containing:
    required: translation, prefix
    optional: language, languages, image, icon, timezone

    `extra_fields` allows to add custom model fields per version
    `extra_fields` is an ordered dict with:
    key must contain '{}' which will be replaced with the version prefix
    value must be a lambda that takes version name and version details (dict)
    and return the model field (ex: lambda _vn, _v: models.CharField(...))

    Utility functions will automatically be available for all the fields.
    Ex: for '{}image' field, there will be a 'get_image_for_version' method
    that takes the version name as parameter and returns the value for that
    version. It doesn't use `defaults`, but you can call the method and follow
    it with `or your_default_value`.

    relevant_{} properties will automatically be available for all the fields.
    Ex: for '{}image' field, there will be an 'relevant_image' property that will automatically
    determine the relevant value to return within the available versions.
    By default, if none of the "relevant" versions have a value, it will try to
    fallback to other versions that have a value. This can be disabled by setting
    `fallbacks` to False for the given field name. Finally, if no value is available
    in any version (or fallback is disabled), it will return what's in `defaults`
    for the given field, or None.

    `fallbacks` is a dict of field name -> bool
    Ex: { '{}image': False }

    `defaults` is a dict of field name -> default value
    Ex: { '{}image': 'default.png' }

    `extra_utils` allows to specify your own utils per version, being properties,
    methods, or variables.
    `extra_utils` is an ordered dict with:
    key must contain '{}' which will be replaced with the version prefix
    value must be a lambda that takes version name and version details (dict)
    and returns yout utility.
    Ex: { '{}duration': lambda _version_name, _version: property(
            lambda _s: _s.getDuration(_version_name)) }
    """
    if not extra_fields:
        extra_fields = {}
    if not extra_utils:
        extra_utils = {}

    default_name = defaults.get('name', None)

    class BaseEventWithVersions(_BaseEvent):

        ############################################################
        # Versions

        FIELDS_PER_VERSION = ['image', 'start_date', 'end_date']

        VERSIONS = versions
        VERSIONS_CHOICES = [(_name, _info['translation']) for _name, _info in VERSIONS.items()]
        c_versions = models.TextField(
            _('Server availability'), blank=True, null=True,
            default=u'"{}"'.format(versions.keys()[0]),
        )

        ############################################################
        # Utils

        # Pick version automatically

        @property
        def relevant_version(self):
            return getRelevantVersion(item=self)

        def get_relevant_name(self, return_version=False):
            return self.get_translated_value_for_relevant_version(
                'name', return_version=return_version,
                default=default_name() if callable(default_name) else default_name,
            )
        relevant_name = property(get_relevant_name)

        image = property(lambda _s: _s.relevant_image)

        def get_field_for_relevant_version(self, field_name, default=None, get_value=None, return_version=False, fallback=True):
            return getFieldForRelevantVersion(
                self, field_name, default=default, get_value=get_value,
                return_version=return_version, fallback=fallback,
            )

        def get_translated_value_for_relevant_version(self, field_name, default=None, return_version=False):
            return getTranslatedValueForRelevantVersion(self, field_name, default=default, return_version=return_version)

        # Specify version

        get_name_for_version = lambda _s, _v: _s.get_relevant_translated_value_for_version('name', _v)

        def get_field_for_version(self, field_name, version_name, get_value=None):
            return getFieldForVersion(self, field_name, version_name, self.VERSIONS[version_name], get_value=get_value)

        def get_status_for_version(self, version_name):
            return getEventStatus(
                self.get_field_for_version('start_date', version_name),
                self.get_field_for_version('end_date', version_name),
            )

        def get_translated_values_for_version(self, field_name, version_name):
            return getTranslatedValuesForVersion(self, field_name, self.VERSIONS[version_name])

        def get_relevant_translated_value_for_version(self, field_name, version_name, fallback=False, default=None):
            return getRelevantTranslatedValueForVersion(
                self, field_name, version_name, self.VERSIONS[version_name], fallback=fallback, default=default,
            )

        ############################################################
        # Class utils

        get_version_name = classmethod(lambda _s, _v: _s.get_version_info(_v, 'translation'))
        get_version_image = classmethod(lambda _s, _v: staticImageURL(_s.get_version_info(_v, 'image')))
        get_version_icon = classmethod(lambda _s, _v: _s.get_version_info(_v, 'icon'))

        @classmethod
        def get_field_name_for_version(self, field_name, version_name):
            return getFieldNameForVersion(field_name, self.VERSIONS[version_name])

        @classmethod
        def get_field_names_all_versions(self, field_name):
            return [
                self.get_field_name_for_version(field_name, version_name)
                for version_name in self.VERSIONS.keys()
            ]

        @classmethod
        def get_version_languages(self, version_name):
            return getLanguagesForVersion(self.VERSIONS[version_name])

        @classmethod
        def get_version_info(self, version_name, field_name, default=None):
            return self.VERSIONS[version_name].get(field_name, default)

        ############################################################
        # Views utils

        @property
        def top_image(self):
            return self.relevant_image_url

        ############################################################
        # Utility method get_{}_for_version for all fields

        def __getattr__(self, name):
            if name.startswith('get_') and name.endswith('_for_version'):
                return lambda version_name: self.get_field_for_version(
                    name[len('get_') : len('_for_version') * -1], version_name,
                )
            elif name.startswith('get_relevant_'):
                field_name = name[len('get_relevant_'):]
                default = defaults.get(field_name, None)
                fallback = fallbacks.get(field_name, True)
                return lambda _self, return_version=False: _self.get_field_for_relevant_version(
                    field_name, default=default() if callable(default) else default,
                    return_version=return_version, fallback=fallback,
                )
            elif name.startswith('relevant_'):
                return getattr(self, u'get_relevant_{}'.format(name[len('relevant_'):]))(self)
            return super(BaseEventWithVersions, self).__getattr__(name)

        ############################################################
        # Unicode

        def __unicode__(self):
            return unicode(self.relevant_name or _('Event'))

        class Meta(MagiModel.Meta):
            abstract = True

    ############################################################
    # Add fields and utils per version

    for version_name, version in versions.items():

        # Add model fields per version
        for field_name, to_field in BASE_EVENT_FIELDS_PER_VERSION.items() + extra_fields.items():
            field = to_field(version_name, version)
            BaseEventWithVersions.add_to_class(getFieldNameForVersion(field_name, version), field)

        # Add utils per version
        for field_name, to_util in BASE_EVENT_UTILS_PER_VERSION.items() + extra_utils.items():
            setattr(BaseEventWithVersions, getFieldNameForVersion(field_name, version), to_util(version_name, version))

    for field_name in BASE_EVENT_FIELDS_PER_VERSION.keys() + extra_fields.keys():
        if not field_name.startswith('_'):

            # Add to FIELDS_PER_VERSION
            BaseEventWithVersions.FIELDS_PER_VERSION.append(field_name)

    return BaseEventWithVersions

############################################################
# Collectible utils

class AutoImageFromParent(object):
    image = property(lambda _s: getattr(_s, _s.collection.item_field_name).image if _s.collection else None)
