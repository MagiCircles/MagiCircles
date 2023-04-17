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
    getVerboseLanguage,
    listUnique,
)
from magi.versions_utils import (
    getRelevantVersion,
    getRelevantVersions,
    getFieldForRelevantVersion,
    getTranslatedValueForRelevantVersion,
    getVersionNeutralFieldName,
    getFieldNameForVersion,
    getFieldNameForVersionAndLanguage,
    getFieldForVersion,
    getFieldTemplateForVersion,
    getValuesPerLanguagesForVersion,
    getValueOfRelevantLanguageForVersion,
    getLanguagesForVersion,
    getTranslatedValuesForVersion,
    getRelevantTranslatedValueForVersion,
)
from magi.default_settings import RAW_CONTEXT

############################################################
# Collectible utils

class AutoImageFromParent(object):
    image = property(lambda _s: getattr(_s, _s.collection.item_field_name).image if _s.collection else None)

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

def to_cached_preferences(
        item,
        twitter_field_name='_cache_owner_preferences_twitter',
        i_status_field_name='_cache_owner_preferences_i_status',
        color_field_name='_cache_owner_color',
):
    try:
        preferences_model = next(
            rel.model for rel in item._meta.get_field('owner').rel.to._meta.get_all_related_objects()
            if rel.get_accessor_name() == 'preferences'
        )
    except StopIteration:
        preferences_model = None
    preferences = AttrDict({})
    if twitter_field_name:
        preferences.update({
            'twitter': getattr(item, twitter_field_name),
        })
    if i_status_field_name:
        preferences.update({
            'i_status': getattr(item, i_status_field_name),
            'status': getattr(item, i_status_field_name),
            'status_color': (
                dict(preferences_model.STATUS_COLORS).get(getattr(item, i_status_field_name), None)
                if preferences_model and getattr(item, i_status_field_name) else None
            ),
            't_status': (
                preferences_model.get_verbose_i('status', getattr(item, i_status_field_name))
                if preferences_model and getattr(item, i_status_field_name) else None
            ),
            'is_premium': (
                getattr(item, i_status_field_name) and getattr(item, i_status_field_name) != 'THANKS'
            ),
        })
    if color_field_name:
        preferences.update({
            'color': getattr(item, color_field_name),
            'localized_color': (
                preferences_model.get_localized_color(getattr(item, color_field_name))
                if preferences_model else None
            ),
            'hex_color': preferences_model.get_hex_color(getattr(item, color_field_name)) if preferences_model else None,
            'rgb_color': preferences_model.get_rgb_color(getattr(item, color_field_name)) if preferences_model else None,
            'css_color': preferences_model.get_css_color(getattr(item, color_field_name)) if preferences_model else None,
        })
    return preferences

# Deprecated - don't use anymore.
class CacheOwner(MagiModel):
    """
    Will provide a cache with basic owner details
    """
    _cached_owner_collection_name = 'user'
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
        updated = False
        if not self._cache_owner_last_update or self._cache_owner_last_update < timezone.now() - datetime.timedelta(days=self._cache_owner_days):
            updated = True
            self.force_cache_owner()
        if updated or not getattr(self, '_cached_owner', None):
            d = {
                'id': self.owner_id,
                'unicode': self._cache_owner_username,
                'username': self._cache_owner_username,
                'email': self._cache_owner_email,
                'preferences': to_cached_preferences(self),
            }
            self._cached_owner = self.cached_json_extra('owner', d)
        return self._cached_owner

    @classmethod
    def cached_owner_extra(self, d):
        d['share_url'] = d['http_item_url']

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

    @property
    def share_url(self):
        return u'{}#{}'.format(self.cached_owner.share_url, self.id)

    # Cache: leaderboard position

    _cache_leaderboards_days = 1
    _cache_leaderboards_last_update = models.DateTimeField(null=True)
    _cache_leaderboard = models.PositiveIntegerField(verbose_name=_('Leaderboard position'), null=True)

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
    level_on_screenshot_upload = models.PositiveIntegerField('Level on screenshot upload', null=True)
    is_hidden_from_leaderboard = models.BooleanField('Hide from leaderboard', default=False, db_index=True)
    is_playground = models.BooleanField(
        _('Playground'), default=False, db_index=True,
        help_text=_('Check this box if this account doesn\'t exist in the game.'),
    )
    IS_PLAYGROUND_HIDE_WHEN_DEFAULT = True

    class Meta:
        abstract = True

############################################################
# ModelWithVersions

BASE_MODEL_FIELDS_PER_VERSION_AND_LANGUAGE = OrderedDict([
    (u'{}image', lambda _version_name, _version, _language=None: models.ImageField(
        string_concat(*([_version['translation'], ' - ', _('Image')] + (
            [' - ', getVerboseLanguage(_language)] if _language else []
        ))),
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True, blank=True,
    )),
    (u'_original_{}image', lambda _version_name, _version, _language=None: models.ImageField(
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True, blank=True,
    )),
])

def getBaseModelWithVersions(
        versions, defaults={}, fallbacks={},
        versions_images_folder='version',
        base_fields=None, fields=None, extra_fields=None,
        base_fields_per_language=BASE_MODEL_FIELDS_PER_VERSION_AND_LANGUAGE,
        fields_per_language=None, extra_fields_per_language=None,
        base_utils=None, utils=None, extra_utils=None,
        base_model_class=MagiModel, default_verbose_name=None,
):
    if fields is None:
        fields = base_fields.copy() if base_fields else {}
    if extra_fields:
        fields.update(extra_fields)
    if fields_per_language is None:
        fields_per_language = base_fields_per_language.copy() if base_fields_per_language else {}
    if extra_fields_per_language:
        fields_per_language.update(extra_fields_per_language)
    if utils is None:
        utils = base_utils.copy() if base_utils else {}
    if extra_utils:
        utils.update(extra_utils)

    has_images = bool([version for version in versions.values() if version.get('image', None)])
    has_icons = bool([version for version in versions.values() if version.get('icon', None)])
    has_languages = bool(getLanguagesForVersion(versions[versions.keys()[0]])) if versions else False
    if not has_languages:
        if extra_fields_per_language:
            if django_settings.DEBUG:
                print '[Warning] extra_fields_per_language was specified in model with versions, but versions don\'t have languages.'
        else:
            fields.update(fields_per_language)

    default_name = defaults.get('name', None)

    class BaseModelWithVersions(MagiModel):

        ############################################################
        # Versions

        NAME_SOURCE_LANGUAGES = listUnique([_l for _sl in [
            getLanguagesForVersion(_version) for _version in versions.values()
        ] for _l in _sl])

        FIELDS_PER_VERSION = []
        ALL_FIELDS_PER_VERSION = []
        FIELDS_PER_VERSION_AND_LANGUAGE = []
        ALL_FIELDS_PER_VERSION_AND_LANGUAGE = []
        FIELDS_PER_VERSION_AND_LANGUAGE_BY_LANGUAGE = {}
        ALL_FIELDS_BY_VERSION = OrderedDict()
        ALL_VERSION_FIELDS_BY_NAME = OrderedDict()

        VERSIONS = versions
        VERSIONS_CHOICES = [(_name, _info['translation']) for _name, _info in VERSIONS.items()]
        c_versions = models.TextField(
            _('Server availability'), blank=True, null=True,
            default=u'"{}"'.format(versions.keys()[0]),
        )
        VERSIONS_HAVE_LANGUAGES = has_languages
        VERSIONS_HAVE_IMAGES = has_images
        VERSIONS_HAVE_ICONS = has_icons

        if has_images:
            VERSIONS_AUTO_IMAGES = True
            VERSIONS_AUTO_IMAGES_FOLDER = versions_images_folder

            @classmethod
            def to_versions_auto_images(self, value):
                if value is None: return None
                return self.VERSIONS[value]['image']

            @classmethod
            def get_version_image(self, version_name):
                return self.get_auto_image('versions', version_name, folder=versions_images_folder)
        else:
            get_version_image = classmethod(lambda _s: None)

        ############################################################
        # Utils

        # Pick version / language automatically

        @property
        def relevant_version(self):
            return getRelevantVersion(item=self)

        @property
        def relevant_versions(self):
            return getRelevantVersions(item=self)

        @property
        def opened_versions(self):
            return getRelevantVersions(
                item=self,
                check_accounts=False,
                check_language=False,
            )

        @property
        def versions_display_order(self):
            # Opened first, then relevant versions, then all other versions
            return [ version_name for version_name in listUnique(
                self.opened_versions
                + self.relevant_versions
                + self.versions
            ) if version_name in self.versions ]

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

        get_name_for_version = lambda _s, _v, _fallback=True: _s.get_relevant_translated_value_for_version(
            'name', _v, fallback=_fallback)

        def get_field_for_version(self, field_name, version_name, get_value=None, language=None):
            return getFieldForVersion(
                self, field_name, version_name, self.VERSIONS[version_name],
                get_value=get_value, language=language,
            )

        def get_status_for_version(self, version_name):
            return getEventStatus(
                self.get_field_for_version('start_date', version_name),
                self.get_field_for_version('end_date', version_name),
                ends_within=self.STATUS_ENDS_WITHIN, starts_within=self.STATUS_STARTS_WITHIN,
            )

        def get_values_per_languages_for_version(self, field_name, version_name, get_value=None):
            return getValuesPerLanguagesForVersion(self, field_name, version_name, self.VERSIONS[version_name], get_value=get_value)

        def get_value_of_relevant_language_for_version(self, field_name, version_name, default=None):
            return getValueOfRelevantLanguageForVersion(self, field_name, version_name, self.VERSIONS[version_name], default=default)

        def get_translated_values_for_version(self, field_name, version_name):
            return getTranslatedValuesForVersion(self, field_name, self.VERSIONS[version_name])

        def get_relevant_translated_value_for_version(self, field_name, version_name, fallback=False, default=None):
            return getRelevantTranslatedValueForVersion(
                self, field_name, version_name, self.VERSIONS[version_name], fallback=fallback, default=default,
            )

        ############################################################
        # Class utils

        get_version_name = classmethod(lambda _s, _v: _s.get_version_info(_v, 'translation'))
        get_version_icon = classmethod(lambda _s, _v: _s.get_version_info(_v, 'icon'))

        @classmethod
        def get_field_name_for_version(self, field_name, version_name):
            return getFieldNameForVersion(field_name, self.VERSIONS[version_name])

        @classmethod
        def get_field_name_for_version_and_language(self, field_name, version_name, language):
            return getFieldNameForVersionAndLanguage(field_name, self.VERSIONS[version_name], language)

        @classmethod
        def get_all_versions_field_names(self, field_name):
            return self.ALL_VERSION_FIELDS_BY_NAME.get(field_name, [])

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
        # Unicode

        def __unicode__(self):
            return (
                unicode(self.relevant_name)
                or default_verbose_name
                or super(BaseModelWithVersions, self).__unicode__()
            )

        class Meta(MagiModel.Meta):
            abstract = True

    ############################################################
    # Add fields and utils per version

    default_ordering = getFieldNameForVersion('{}start_date', versions[versions.keys()[0]])

    BaseModelWithVersions._versions_by_prefixes = {
        version['prefix']: version_name
        for version_name, version in versions.items()
    }

    for version_name, version in versions.items():
        BaseModelWithVersions.ALL_FIELDS_BY_VERSION[version_name] = []

        for template_field_name, to_field in fields.items():
            # Add model fields per version
            field_name = getFieldNameForVersion(template_field_name, version)
            field = to_field(version_name, version)
            BaseModelWithVersions.add_to_class(field_name, field)
            # Add to ALL_FIELDS_PER_VERSION
            BaseModelWithVersions.ALL_FIELDS_PER_VERSION.append(field_name)
            # Add to ALL_FIELDS_BY_VERSION
            BaseModelWithVersions.ALL_FIELDS_BY_VERSION[version_name].append(field_name)
            # Add to ALL_VERSION_FIELDS_BY_NAME
            if template_field_name not in BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME:
                BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME[template_field_name] = []
            BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME[template_field_name].append(field_name)
            # Add default ordering if matches
            if field_name == default_ordering:
                pass # BaseModelWithVersions.Meta.ordering = [default_ordering]

        for language in getLanguagesForVersion(version):
            for template_field_name, to_field in fields_per_language.items():
                # Add model fields per language
                field = to_field(version_name, version, language)
                field_name = getFieldNameForVersionAndLanguage(template_field_name, version, language)
                BaseModelWithVersions.add_to_class(field_name, field)
                # Add to FIELDS_PER_VERSION_AND_LANGUAGE_BY_LANGUAGE
                if language not in BaseModelWithVersions.FIELDS_PER_VERSION_AND_LANGUAGE_BY_LANGUAGE:
                    BaseModelWithVersions.FIELDS_PER_VERSION_AND_LANGUAGE_BY_LANGUAGE[language] = []
                BaseModelWithVersions.FIELDS_PER_VERSION_AND_LANGUAGE_BY_LANGUAGE[language].append(field_name)
                # Add to ALL_FIELDS_PER_VERSION_AND_LANGUAGE
                BaseModelWithVersions.ALL_FIELDS_PER_VERSION_AND_LANGUAGE.append(field_name)
                # Add to ALL_FIELDS_BY_VERSION
                BaseModelWithVersions.ALL_FIELDS_BY_VERSION[version_name].append(field_name)
                # Add to ALL_VERSION_FIELDS_BY_NAME
                if template_field_name not in BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME:
                    BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME[template_field_name] = []
                BaseModelWithVersions.ALL_VERSION_FIELDS_BY_NAME[template_field_name].append(field_name)

        # Add utils per version
        for field_name, to_util in utils.items():
            template = getFieldTemplateForVersion(field_name)
            new_field_name = template.format(version['prefix'].upper() if template.isupper() else version['prefix'])
            setattr(BaseModelWithVersions, new_field_name, to_util(version_name, version))

        def _get_relevant_language_for_version(field_name, version_name):
            return lambda item: item.get_value_of_relevant_language_for_version(field_name, version_name)

        def _get_relevant(field_name, default, fallback):
            return lambda item, return_version=False: item.get_field_for_relevant_version(
                field_name,
                default=default() if callable(default) else default,
                return_version=return_version, fallback=fallback,
            )

        def _add_relevant_utils(field_name):
            neutral_field_name = getVersionNeutralFieldName(field_name)
            l = _get_relevant(field_name, defaults.get(field_name, None), fallbacks.get(field_name, True))
            setattr(BaseModelWithVersions, u'get_relevant_{}'.format(neutral_field_name), l)
            setattr(BaseModelWithVersions, u'relevant_{}'.format(neutral_field_name), property(l))

        def _get_for_version(field_name):
            return lambda item, version_name: item.get_field_for_version(field_name, version_name)

        def _get_for_version_and_language(field_name):
            return lambda item, version_name, language: item.get_field_for_version(field_name, version_name, language)

        def _get_for_version_with_relevant_language(field_name):
            return lambda item, version_name: item.get_value_of_relevant_language_for_version(field_name, version_name)

    for field_name in fields.keys():
        if not field_name.startswith('_'):

            # Add to FIELDS_PER_VERSION
            BaseModelWithVersions.FIELDS_PER_VERSION.append(field_name)

            # Add utils
            neutral_field_name = getVersionNeutralFieldName(field_name)
            setattr(BaseModelWithVersions, u'get_{}_for_version'.format(
                neutral_field_name), _get_for_version(field_name))
            _add_relevant_utils(field_name)

    for field_name in fields_per_language.keys():
        if not field_name.startswith('_'):

            # Add to FIELDS_PER_VERSION_AND_LANGUAGE
            BaseModelWithVersions.FIELDS_PER_VERSION_AND_LANGUAGE.append(field_name)

            # Add utils
            for version_name, version in versions.items():
                version_field_name = getFieldNameForVersion(field_name, version)
                setattr(BaseModelWithVersions, version_field_name, property(
                    _get_relevant_language_for_version(field_name, version_name)))
            neutral_field_name = getVersionNeutralFieldName(field_name)
            setattr(BaseModelWithVersions, u'get_{}_for_version_and_language'.format(
                neutral_field_name), _get_for_version_and_language(field_name))
            setattr(BaseModelWithVersions, u'get_{}_for_version'.format(
                neutral_field_name), _get_for_version_with_relevant_language(field_name))
            _add_relevant_utils(field_name)

    return BaseModelWithVersions

############################################################
# BaseEvent

class _BaseEvent(MagiModel):
    collection_name = 'event'
    TRANSLATED_FIELDS = ['name', 'm_description']

    owner = models.ForeignKey(User, related_name='added_%(class)ss')

    ############################################################
    # Name

    name = models.CharField(_('Title'), max_length=100, null=True)
    NAMES_CHOICES = ALL_ALT_LANGUAGES
    d_names = models.TextField(_('Title'), null=True)

    ############################################################
    # Description

    m_description = models.TextField(_('Details'), null=True)
    M_DESCRIPTIONS_CHOICES = ALL_ALT_LANGUAGES
    d_m_descriptions = models.TextField(_('Details'), null=True)
    _cache_description = models.TextField(null=True)

    STATUS_STARTS_WITHIN = 3
    STATUS_ENDS_WITHIN = 3

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

    get_status = lambda _s: getEventStatus(
        _s.start_date, _s.end_date, ends_within=_s.STATUS_ENDS_WITHIN, starts_within=_s.STATUS_STARTS_WITHIN)
    status = property(get_status)

    class Meta(MagiModel.Meta):
        abstract = True
        ordering = ['-start_date']

BASE_EVENT_FIELDS_PER_VERSION = OrderedDict([
    (u'{}start_date', lambda _version_name, _version: models.DateTimeField(
        string_concat(_version['translation'], ' - ', _('Beginning')), null=True,
    )),
    (u'{}end_date', lambda _version_name, _version: models.DateTimeField(
        string_concat(_version['translation'], ' - ', _('End')), null=True,
    )),
])

BASE_EVENT_FIELDS_PER_VERSION_AND_LANGUAGE = OrderedDict([
    (u'{}image', lambda _version_name, _version, _language=None: models.ImageField(
        string_concat(*([_version['translation'], ' - ', _('Image')] + (
            [' - ', getVerboseLanguage(_language)] if _language else []
        ))),
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True,
    )),
    (u'_original_{}image', lambda _version_name, _version, _language=None: models.ImageField(
        upload_to=uploadItem(u'event/{}'.format(_version_name.lower())), null=True,
    )),
])

_timezones_lambda = lambda _version_name, _version: _version.get(
    'timezones', [_version['timezone']] if _version.get('timezone', None) else None)

BASE_EVENT_UTILS_PER_VERSION = OrderedDict([
    (u'{}name', lambda _version_name, _version: property(lambda _s: _s.get_name_for_version(_version_name))),
    (u'{}status', lambda _version_name, _version: property(lambda _s: _s.get_status_for_version(_version_name))),
    (u'{}START_DATE_DEFAULT_TIMEZONES', _timezones_lambda),
    (u'{}END_DATE_DEFAULT_TIMEZONES', _timezones_lambda),
])

def getBaseEventWithVersions(
        versions, defaults={}, fallbacks={},
        fields=None, extra_fields=None,
        fields_per_language=None, extra_fields_per_language=None,
        utils=None, extra_utils=None,
):
    """
    https://github.com/MagiCircles/MagiCircles/wiki/Events
    """
    return getBaseModelWithVersions(
        versions, defaults=defaults, fallbacks=fallbacks,
        base_fields=BASE_EVENT_FIELDS_PER_VERSION,
        fields=fields, extra_fields=extra_fields,
        base_fields_per_language=BASE_EVENT_FIELDS_PER_VERSION_AND_LANGUAGE,
        fields_per_language=fields_per_language, extra_fields_per_language=extra_fields_per_language,
        base_utils=BASE_EVENT_UTILS_PER_VERSION, utils=utils, extra_utils=extra_utils,
        base_model_class=_BaseEvent, default_verbose_name=_('Event'),
    )

class BaseEventParticipation(AccountAsOwnerModel, AutoImageFromParent):
    collection_name = 'eventparticipation'

    account = models.ForeignKey('{}.Account'.format(django_settings.SITE), related_name='%(class)ss', verbose_name=_('Account'))

    class Meta(MagiModel.Meta):
        abstract = True
