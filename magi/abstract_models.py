import datetime
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.conf import settings as django_settings
from django.utils import timezone
from magi.item_model import MagiModel, get_image_url_from_path
from magi.utils import AttrDict
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
            'unicode': unicode(self),
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
                't_status': dict(preferences_model.STATUS_CHOICES)[self._cache_owner_preferences_i_status] if preferences_model and self._cache_owner_preferences_i_status else None,
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
    # If you're willing to add a unique code allowing users to find the real account in the game,
    # use a field name "friend_id"
    collection_name = 'account'

    owner = models.ForeignKey(User, related_name='accounts')
    creation = models.DateTimeField(_('Join date'), auto_now_add=True)
    nickname = models.CharField(_('Nickname'), max_length=200, null=True, help_text=_('Give a nickname to your account to easily differentiate it from your other accounts when you\'re managing them.'))
    start_date = models.DateField(_('Start date'), null=True)
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

    def update_cache_leaderboards(self):
        self._cache_leaderboards_last_update = timezone.now()
        self._cache_leaderboard = type(self).objects.filter(level__gt=self.level).values('level').distinct().count() + 1

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
