from collections import OrderedDict
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from magi.utils import justReturn
from magi.abstract_models import CacheOwner
from magi.item_model import MagiModel, BaseMagiModel, i_choices

class Account(MagiModel):
    collection_name = 'account'

    owner = models.ForeignKey(User, related_name='accounts')
    creation = models.DateTimeField(auto_now_add=True)
    level = models.PositiveIntegerField(_("Level"), null=True)

    def __unicode__(self):
        return u'#{} Level {}'.format(self.id, self.level)

class IChoicesTest(BaseMagiModel):
    ATTRIBUTE_CHOICES = (
        'smile',
        'pure',
        'cool',
    )
    i_attribute = models.PositiveIntegerField(choices=i_choices(ATTRIBUTE_CHOICES), default=0)

    POWER_CHOICES = (
        _('Happy'),
        _('Cool'),
        _('Rock'),
    )
    i_power = models.PositiveIntegerField(choices=i_choices(POWER_CHOICES), default=0)

    SUPER_POWER_CHOICES = (
        ('happy', _('Happy')),
        ('cool', _('Cool')),
        ('rock', _('Rock')),
    )
    i_super_power = models.PositiveIntegerField(choices=i_choices(SUPER_POWER_CHOICES), default=0)

    i_rarity = models.PositiveIntegerField(choices=i_choices(['N', 'R', 'SR']), default=0)

    LANGUAGE_CHOICES = (
        ('en', _('English')),
        ('es', _('Spanish')),
        ('ru', _('Russian')),
        ('it', _('Italian')),
    )
    LANGUAGE_WITHOUT_I_CHOICES = True
    i_language = models.CharField(_('Language'), max_length=10, choices=LANGUAGE_CHOICES, default='en')


    NOTIFICATIONS = [
        ('like', {
            'title': _(u'When someone likes your activity.'),
            'icon': 'heart',
        }),
        ('follow', {
            'title': _(u'When someone follows you.'),
            'icon': 'users',
        }),
    ]
    NOTIFICATIONS_DICT = dict(NOTIFICATIONS)
    NOTIFICATION_CHOICES = [(key, _notification['title']) for key, _notification in NOTIFICATIONS]
    i_notification = models.PositiveIntegerField(_('Notification type'), choices=i_choices(NOTIFICATION_CHOICES), default=0)

    def notification_value(self, key):
        """
        Get the dictionary value for this key, for the current notification notification.
        """
        return self.NOTIFICATIONS_DICT.get(self.notification, {}).get(key, u'')

    @property
    def notification_icon(self):
        return self.notification_value('icon')

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
    PLAY_WITH_CHOICES = [(_name, _info['translation']) for _name, _info in PLAY_WITH.items()]
    i_play_with = models.PositiveIntegerField(_('Play with'), choices=i_choices(PLAY_WITH_CHOICES), null=True)

class CCSVTest(BaseMagiModel):

    c_data = models.TextField(blank=True, null=True)

    ABILITIES_CHOICES = (
        ('fly', _('Fly')),
        ('dance', _('Dance')),
        ('sing', _('Sing')),
        ('heal', _('Heal')),
    )
    c_abilities = models.TextField(blank=True, null=True)

    TAGS_CHOICES = (
        'christmas',
        'party',
        'NSFW'
    )
    c_tags = models.TextField(blank=True, null=True)

class Book(CacheOwner):
    owner = models.ForeignKey(User, related_name='books')

class Chapter(CacheOwner):
    book = models.ForeignKey(Book, related_name='chapters')
    fk_as_owner = 'book'

    @property
    def owner(self):
        return self.book.cached_owner

    @property
    def owner_id(self):
        return self.book.owner_id

class Paragraph(CacheOwner):
    chapter = models.ForeignKey(Chapter, related_name='paragraphs')
    fk_as_owner = 'chapter'
    selector_to_owner = classmethod(justReturn('chapter__book__owner'))

    @property
    def owner(self):
        return self.chapter.cached_owner

    @property
    def owner_id(self):
        return self.chapter.cached_owner.id
