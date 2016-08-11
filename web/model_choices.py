from django.utils.translation import ugettext_lazy as _, string_concat
from web.settings import DONATORS_STATUS_CHOICES, ACTIVITY_TAGS
from django.conf import settings as django_settings

############################################################
# Languages

def languageToString(language): return dict(django_settings.LANGUAGES)[language]

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
def statusToString(status): return dict(STATUS_CHOICES)[status]

def statusToColor(status):
    if status == 'SUPPORTER': return '#4a86e8'
    elif status == 'LOVER': return '#ff53a6'
    elif status == 'AMBASSADOR': return '#a8a8a8'
    elif status == 'PRODUCER': return '#c98910'
    elif status == 'DEVOTEE': return '#c98910'
    return ''

def statusToColorString(status):
    if status == 'SUPPORTER': return _('blue')
    elif status == 'LOVER': return _('pink')
    elif status == 'AMBASSADOR': return _('shiny Silver')
    elif status == 'PRODUCER': return _('shiny Gold')
    elif status == 'DEVOTEE': return _('shiny Gold')
    return ''

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
def linkToString(link):
    if link in dict(LINK_CHOICES):
        return dict(LINK_CHOICES)[link]
    return link

LINK_URLS = {
    'Location': 'http://maps.google.com/?q={}',
    'twitter': 'http://twitter.com/{}',
    'facebook': 'https://www.facebook.com/{}',
    'reddit': 'http://www.reddit.com/user/{}',
    'schoolidolu': 'http://schoolido.lu/user/{}/',
    'frgl': 'http://fr.gl/user/{}/',
    'stardustrun': 'http://stardust.run/user/{}/',
    'line': 'http://line.me/#{}',
    'tumblr': 'http://{}.tumblr.com/',
    'twitch': 'http://twitch.tv/{}',
    'steam': 'http://steamcommunity.com/id/{}',
    'instagram': 'https://instagram.com/{}/',
    'youtube': 'https://www.youtube.com/user/{}',
    'github': 'https://github.com/{}',
}

LINK_RELEVANCE_CHOICES = (
    (0, _('Never')),
    (1, _('Sometimes')),
    (2, _('Often')),
    (3, _('Every single day')),
)
def linkRelevanceToString(rel): return dict(LINK_RELEVANCE_CHOICES)[rel]

############################################################
# Notifications

NOTIFICATION_LIKE = 0
NOTIFICATION_FOLLOW = 1

NOTIFICATION_CHOICES = (
    (NOTIFICATION_LIKE, _('{} liked your activity: {}.')),
    (NOTIFICATION_FOLLOW, _('{} just followed you.')),
)

NOTIFICATION_DICT = dict(NOTIFICATION_CHOICES)

NOTIFICATION_TITLES = {
    NOTIFICATION_LIKE: _('When someone likes your activity.'),
    NOTIFICATION_FOLLOW: _('When someone follows you.'),
}

NOTIFICATION_URLS = {
    NOTIFICATION_LIKE: '/activity/{}/{}/',
    NOTIFICATION_FOLLOW: '/user/{}/{}/',
}

NOTIFICATION_ICONS = {
    NOTIFICATION_LIKE: 'heart',
    NOTIFICATION_FOLLOW: 'users',
}

############################################################
# Tags

def tagToString(tag): return dict(ACTIVITY_TAGS)[tag]

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

def reportStatusToString(status): return dict(REPORT_STATUSES)[status]
