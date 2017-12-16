from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from magi.item_model import MagiModel

############################################################
# AccountAsOwnerModel

class AccountAsOwnerModel(MagiModel):
    """
    Will provide a cache when item doesn't have an owner but has an account.
    You need to provide the account field in your model:
    account = models.ForeignKey(Account, verbose_name=_('Account'))
    """
    fk_as_owner = 'account'

    _cache_account_days = 200 # Change to a lower value if owner can change
    _cache_account_last_update = models.DateTimeField(null=True)
    _cache_account_owner_id = models.PositiveIntegerField(null=True)

    def update_cache_account(self):
        self._cache_account_last_update = timezone.now()
        self._cache_account_owner_id = self.account.owner_id

    def force_cache_account(self):
        self.update_cache_account()
        self.save()

    @property
    def cached_account(self):
        if (not self._cache_account_last_update
            or self._cache_account_last_update < timezone.now() - datetime.timedelta(days=self._cache_account_days)):
            self.force_cache_account()
        return AttrDict({
            'pk': self.account_id,
            'id': self.account_id,
            'unicode': u'#{}'.format(self.account_id),
            'owner': AttrDict({
                'id': self._cache_account_owner_id,
                'pk': self._cache_account_owner_id,
            }),
        })

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
        self._cache_owner_username = self.owner.username
        self._cache_owner_email = self.owner.email
        self._cache_owner_preferences_i_status = self.owner.preferences.i_status
        self._cache_owner_preferences_twitter = self.owner.preferences.twitter
        self._cache_owner_color = self.owner.preferences.color

    def force_cache_owner(self):
        self.update_cache_owner()
        self.save()

    @property
    def cached_owner(self):
        if not self._cache_owner_last_update or self._cache_owner_last_update < timezone.now() - datetime.timedelta(days=self._cache_owner_days):
            self.force_cache_owner()
        return AttrDict({
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
                'color': self._cache_owner_color,
            }),
        })

    class Meta:
        abstract = True

############################################################
# BaseAccount

class BaseAccount(CacheOwner):
    collection_name = 'account'

    owner = models.ForeignKey(User, related_name='accounts')
    creation = models.DateTimeField(_('Join Date'), auto_now_add=True)
    start_date = models.DateField(_('Start Date'), null=True)
    level = models.PositiveIntegerField(_("Level"), null=True)

    def __unicode__(self):
        return u'#{} {}'.format(self.id, u'Level {}'.format(self.level) if self.level else '')

    class Meta:
        abstract = True
