from collections import OrderedDict
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _, get_language
from django.db import models
from magi.utils import justReturn
from magi.abstract_models import CacheOwner
from magi.item_model import MagiModel, BaseMagiModel, i_choices
from magi.utils import uploadItem

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

class Idol(MagiModel):
    collection_name = 'idol'

    owner = models.ForeignKey(User, related_name='added_idols')
    name = models.CharField(max_length=100, unique=True)
    japanese_name = models.CharField(max_length=100, null=True)
    d_names = models.TextField(null=True)
    image = models.ImageField(upload_to=uploadItem('idols'))

class Card(MagiModel):
    owner = models.ForeignKey(User, related_name='added_cards')

    idol = models.ForeignKey(Idol, related_name='cards', null=True)

    # Cache idol

    _cache_idol_days = 10
    _cache_idol_last_update = models.DateTimeField(null=True)
    _cache_j_idol = models.TextField(null=True)

    @classmethod
    def cached_idols_pre(self, d):
        d['unicode'] = d['japanese_name'] if get_language() == 'ja' else d['name']
        return d

    def to_cache_idol(self):
        if not self.idol_id:
            return None
        return {
            'id': self.idol.id,
            'name': self.idol.name,
            'names': self.idol.names,
            'japanese_name': self.idol.japanese_name,
            'image': str(self.idol.image),
        }

    # Cache idol name (it wouldn't make sense in a real life scenario to cache name when json cache exists)

    _cache_idol_name = models.CharField(max_length=100, null=True)

    def to_cache_idol_name(self):
        return self.idol.name if self.idol_id else None

    # Cache idol japanese name (it wouldn't make sense in a real life scenario to cache name when json cache exists)

    _cache_idol_japanese_name_days = 20
    _cache_idol_japanese_name_last_update = models.DateTimeField(null=True)
    _cache_idol_japanese_name = models.CharField(max_length=100, null=True)

    def to_cache_idol_japanese_name(self):
        return self.idol.japanese_name if self.idol_id else None

    # Cache gachas

    _cached_gachas_collection_name = 'gacha'
    _cache_gachas_days = 20
    _cache_gachas_last_update = models.DateTimeField(null=True)
    _cache_j_gachas = models.TextField(null=True)
    _cache_gachas_fk_class = classmethod(lambda _s: Gacha)

    def to_cache_gachas(self):
        gachas = []
        for gacha in Gacha.objects.filter(card_id=self.id):
            gachas.append({
                'id': gacha.id,
                'name': gacha.name,
                'image': str(gacha.image),
                'i_attribute': gacha.i_attribute,
                'i_power': gacha.i_power,
                'i_super_power': gacha.i_super_power,
                'i_rarity': gacha.i_rarity,
            })
        return gachas if gachas else None

    # Cache gachas names (it wouldn't make sense in a real life scenario to cache names when json cache exists)

    _cache_c_gacha_names = models.TextField(null=True)

    def to_cache_gacha_names(self):
        return Gacha.objects.filter(card_id=self.id).values_list('name', flat=True)

    # Cache gachas ids (it wouldn't make sense in a real life scenario to cache ids when json cache exists)

    _cache_gacha_ids_days = 20
    _cache_gacha_ids_last_update = models.DateTimeField(null=True)
    _cache_c_gacha_ids = models.TextField(null=True)

    def to_cache_gacha_ids(self):
        return Gacha.objects.filter(card_id=self.id).values_list('id', flat=True)

    @classmethod
    def cached_gacha_ids_map(self, i):
        return int(i)

    # Cache total gachas (it wouldn't make sense in a real life scenario to cache total when json cache exists)

    _cache_total_gachas_update_on_none = True
    _cache_total_gachas = models.PositiveIntegerField(null=True)

    def to_cache_total_gachas(self):
        return self.gachas.count()

class Gacha(MagiModel):
    collection_name = 'gacha'

    owner = models.ForeignKey(User, related_name='added_gachas')
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to=uploadItem('gacha'))

    card = models.ForeignKey(Card, related_name='gachas', null=True)

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

class TranslatedNames(BaseMagiModel):
    # With choices, translatable
    name = models.CharField(max_length=100)
    NAMES_CHOICES = (
        ('ja', _('Japanese')),
        ('ru', _('Russian')),
        ('zh-hans', _('Chinese')),
    )
    korean_name = models.CharField(max_length=100, null=True)
    d_names = models.TextField(null=True)

    # With choices but not translation
    COLOR_CHOICES = (
        'blue',
        'green',
        'red',
    )
    d_colors = models.TextField(null=True)

    # No choices
    d_items = models.TextField(null=True)
