from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _
from magi.django_translated import t
from django.conf import settings

RAW_CONTEXT = {
    'debug': settings.DEBUG,
    'site': settings.SITE,
    'extends': 'base.html',
    'forms': {},
    'form': None,
}

_usernameRegexp = '[\w.@+-]+'

############################################################
# Javascript translated terms

FORCE_ADD_TO_TRANSLATION = [
    _('Liked this activity'),
    _('Loading'), _('No result.'),
    _('Local time'),
    _('days'), _('hours'), _('minutes'), _('seconds'),
]

DEFAULT_JAVASCRIPT_TRANSLATED_TERMS = [
    'Liked this activity',
    'Loading', 'No result.',
    'You can\'t cancel this action afterwards.', 'Confirm', 'Cancel',
    'days', 'hours', 'minutes', 'seconds',
    'Local time',
]

############################################################
# Navbar lists

DEFAULT_ENABLED_NAVBAR_LISTS = OrderedDict([
    ('you', {
        'title': lambda context: context['request'].user.username if context['request'].user.is_authenticated() else _('You'),
        'icon': 'profile',
        'order': ['user', 'settings', 'logout', 'login', 'signup'],
        'url': '/me/',
    }),
    ('more', {
        'title': '',
        'icon': 'more',
        'order': ['about', 'donate_list', 'help', 'map', 'report_list', 'badge_list'],
        'url': '/about/',
    }),
])

############################################################
# Enabled pages

DEFAULT_ENABLED_PAGES = OrderedDict([
    ('index', {
        'custom': False,
        'enabled': False,
        'navbar_link': False,
    }),
    ('login', {
        'custom': False,
        'title': _('Login'),
        'navbar_link_list': 'you',
        'logout_required': True,
    }),
    ('signup', {
        'custom': False,
        'title': _('Sign Up'),
        'navbar_link_list': 'you',
        'logout_required': True,
    }),
    ('user', {
        'custom': False,
        'title': _('Profile'),
        'icon': 'profile',
        'url_variables': [
            ('pk', '\d+', lambda (context): str(context['request'].user.id)),
            ('username', _usernameRegexp, lambda (context): context['request'].user.username),
        ],
        'navbar_link_list': 'you',
        'authentication_required': True,
    }),
    ('settings', {
        'title': _('Settings'),
        'custom': False,
        'icon': 'settings',
        'navbar_link_list': 'you',
        'authentication_required': True,
    }),
    ('logout', {
        'custom': False,
        'title': _('Logout'),
        'icon': 'logout',
        'navbar_link_list': 'you',
        'authentication_required': True,
    }),
    ('about', [
        {
            'title': _('About'),
            'custom': False,
            'icon': 'about',
            'navbar_link_list': 'more',
        },
        {
            'ajax': True,
            'title': _('About'),
            'custom': False,
            'icon': 'about',
            'navbar_link_list': 'more',
        },
    ]),
    ('prelaunch', {
        'title': _('Coming soon'),
        'custom': False,
        'navbar_link': False,
    }),
    ('about_game', {
        'ajax': True,
        'title': _('About the game'),
        'custom': False,
        'icon': 'about',
    }),
    ('map', {
        'title': _('Map'),
        'custom': False,
        'icon': 'world',
        'navbar_link_list': 'more',
    }),
    ('help', [
        {
            'custom': False,
            'title': _('Help'),
            'icon': 'help',
            'navbar_link_list': 'more',
        },
        {
            'custom': False,
            'title': _('Help'),
            'url_variables': [
                ('wiki_url', '[^/]+'),
            ],
            'navbar_link': False,
        },
    ]),
    ('wiki', [
        {
            'enabled': False,
            'custom': False,
            'title': _('Wiki'),
            'icon': 'about',
        },
        {
            'enabled': False,
            'custom': False,
            'icon': 'about',
            'title': _('Wiki'),
            'url_variables': [
                ('wiki_url', '[^/]+'),
            ],
            'navbar_link': False,
        },
    ]),
    ('deletelink', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
    }),
    ('likeactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
    }),
    ('follow', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('username', _usernameRegexp),
        ],
    }),
    ('twitter_avatar', {
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('twitter', '[^/]+'),
        ]
    }),
    ('changelanguage', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
    }),
    ('moderatereport', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('report', '\d+'),
            ('action', '\w+'),
        ],
    }),
    ('reportwhatwillbedeleted', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('report', '\d+'),
        ],
    }),
    ('successedit', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
    }),
    ('successadd', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
    }),
    ('successdelete', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
    }),
])

############################################################
# Default profile tabs

DEFAULT_PROFILE_TABS = OrderedDict([
    ('account', {
        'name': _('Accounts'),
        'icon': 'users',
    }),
    ('activity', {
        'name': _('Activities'),
        'icon': 'comments',
        'callback': 'profileLoadActivities',
    }),
    ('badge', {
        'name': _('Badges'),
        'icon': 'achievement',
        'callback': 'loadBadges',
    }),
])

############################################################
# Default navbar ordering

DEFAULT_NAVBAR_ORDERING = [
    'account_list',
    'you',
    'more',
]

############################################################
# Default prelaunch enabled pages

DEFAULT_PRELAUNCH_ENABLED_PAGES = [
    'login',
    'signup',
    'prelaunch',
    'about',
    'about_game',
    'changelanguage',
    'help',
]
