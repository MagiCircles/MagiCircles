from django.utils.translation import ugettext_lazy as _, string_concat
from web.settings import DONATORS_STATUS_CHOICES, ACTIVITY_TAGS
from django.conf import settings as django_settings

############################################################
# Languages

LANGUAGES_DICT = dict(django_settings.LANGUAGES)

############################################################
# Donator statuses choices

if DONATORS_STATUS_CHOICES:
    STATUS_CHOICES = DONATORS_STATUS_CHOICES
else:
    STATUS_CHOICES = (
        ('THANKS', 'Thanks'),
        ('SUPPORTER', _('Player')),
        ('LOVER', _('Super Player')),
        ('AMBASSADOR', _('Extreme Player')),
        ('PRODUCER', _('Master Player')),
        ('DEVOTEE', _('Ultimate Player')),
    )
STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

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

############################################################
# Links

LINK_CHOICES = (
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
LINK_CHOICES_DICT = dict(LINK_CHOICES)

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

LINK_RELEVANCE_CHOICES = (
    (0, _('Never')),
    (1, _('Sometimes')),
    (2, _('Often')),
    (3, _('Every single day')),
)
LINK_RELEVANCE_CHOICES_DICT = dict(LINK_RELEVANCE_CHOICES)

############################################################
# Notifications

NOTIFICATION_LIKE = 0
NOTIFICATION_FOLLOW = 1

NOTIFICATION_CHOICES = (
    (NOTIFICATION_LIKE, _(u'{} liked your activity: {}.')),
    (NOTIFICATION_FOLLOW, _(u'{} just followed you.')),
)

NOTIFICATION_DICT = dict(NOTIFICATION_CHOICES)

NOTIFICATION_TITLES = {
    NOTIFICATION_LIKE: _(u'When someone likes your activity.'),
    NOTIFICATION_FOLLOW: _(u'When someone follows you.'),
}

NOTIFICATION_OPEN_SENTENCES = {
    NOTIFICATION_LIKE : lambda n: _('Open {thing}').format(thing=_('Activity')),
    NOTIFICATION_FOLLOW: lambda n: _('Open {thing}').format(thing=_('Profile')),
}

NOTIFICATION_URLS = {
    NOTIFICATION_LIKE: u'/activity/{}/{}/',
    NOTIFICATION_FOLLOW: u'/user/{}/{}/',
}

NOTIFICATION_ICONS = {
    NOTIFICATION_LIKE: 'heart',
    NOTIFICATION_FOLLOW: 'users',
}

############################################################
# Tags

ACTIVITY_TAGS_DICT =  dict(ACTIVITY_TAGS if ACTIVITY_TAGS else [])

############################################################
# Reports

REPORT_STATUS_PENDING = 0
REPORT_STATUS_DELETED = 1
REPORT_STATUS_EDITED = 2
REPORT_STATUS_IGNORED = 3

REPORT_STATUSES = (
    (REPORT_STATUS_PENDING, 'Pending'), # No staff took care of it
    (REPORT_STATUS_DELETED, 'Deleted'), # Staff decided to delete the thing and notify the owner
    (REPORT_STATUS_EDITED, 'Edited'), # Staff decided to edit the thing and notify the owner
    (REPORT_STATUS_IGNORED, 'Ignored'), # Staff decided to ignore the report
)
REPORT_STATUSES_DICT = dict(REPORT_STATUSES)

############################################################
# Badges

BADGE_RANK_BRONZE = 1
BADGE_RANK_SILVER = 2
BADGE_RANK_GOLD = 3

BADGE_RANK_CHOICES = (
    (BADGE_RANK_BRONZE, _('Bronze')),
    (BADGE_RANK_SILVER, _('Silver')),
    (BADGE_RANK_GOLD, _('Gold')),
)
