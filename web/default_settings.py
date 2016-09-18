from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _, string_concat
from web.django_translated import t
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Prefetch, Count, Q
from django.conf.urls import url
from web.middleware.httpredirect import HttpRedirectException

RAW_CONTEXT = {
    'debug': settings.DEBUG,
    'site': settings.SITE,
    'extends': 'base.html',
}

_usernameRegexp = '[\w.@+-]+'

############################################################
# Javascript translated terms

DEFAULT_JAVASCRIPT_TRANSLATED_TERMS = [
    'All', 'Only', 'None',
    'Unknown', 'Yes', 'No',
    'Liked this activity',
    'Loading', 'No result.',
]

############################################################
# Navbar lists

DEFAULT_ENABLED_NAVBAR_LISTS = OrderedDict([
    ('you', {
        'title': lambda context: context['request'].user.username if context['request'].user.is_authenticated() else _('You'),
        'icon': 'profile',
    }),
    ('more', {
        'title': '',
        'icon': 'more',
    }),
])

############################################################
# Enabled collections

def _accountBeforeSave(request, instance, type=None):
    instance.owner = request.user
    return instance

def _accountRedirectAfter(request, instance, ajax=False):
    return '{}#{}'.format(request.user.item_url, instance.id)

def _accountRedirectAfterDelete(request, instance, ajax=False):
    return request.user.item_url

def _userItemFilterQuerySet(queryset, parameters, request):
    if request.user.is_authenticated():
        queryset = queryset.extra(select={
            'followed': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = {} AND user_id = auth_user.id'.format(request.user.preferences.id),
        })
        queryset = queryset.extra(select={
            'is_followed_by': 'SELECT COUNT(*) FROM web_userpreferences_following WHERE userpreferences_id = (SELECT id FROM web_userpreferences WHERE user_id = auth_user.id) AND user_id = {}'.format(request.user.id),
        })
    queryset = queryset.annotate(total_following=Count('preferences__following'), total_followers=Count('followers'))
    queryset = queryset.select_related('preferences', 'favorite_character1', 'favorite_character2', 'favorite_character3')
    queryset = queryset.prefetch_related(Prefetch('accounts', to_attr='all_accounts'), Prefetch('links', to_attr='all_links'))
    return queryset

def _activitiesQuerysetWithLikesAndLiked(queryset, parameters, request):
    if request.user.is_authenticated():
        queryset = queryset.extra(select={
            'liked': 'SELECT COUNT(*) FROM web_activity_likes WHERE activity_id = web_activity.id AND user_id = {}'.format(request.user.id),
        })
    if 'tags' in parameters:
        for tag in parameters['tags'].split(','):
            queryset = queryset.filter(tags_string__contains='"{}"'.format(tag))
    if 'owner_id' in parameters:
        queryset = queryset.filter(owner_id=parameters['owner_id'])
    if 'feed' in parameters and request.user.is_authenticated():
        queryset = queryset.filter(Q(owner__in=request.user.preferences.following.all()) | Q(owner_id=request.user.id))
    elif request.user.is_authenticated() and request.user.preferences.view_activities_language_only:
        queryset = queryset.filter(language=request.LANGUAGE_CODE)
    queryset = queryset.annotate(total_likes=Count('likes'))
    return queryset

def _notificationsFilter(queryset, parameters, request):
    if not request.user.is_authenticated():
        raise HttpRedirectException('/signup/?next=/notifications/')
    if 'ajax_modal_only' in parameters:
        queryset = queryset.filter(seen=False)
    else:
        queryset = queryset.filter(seen=True)
    return queryset.filter(owner=request.user)

DEFAULT_ENABLED_COLLECTIONS = OrderedDict([
    ('account', {
        'title': _('Account'),
        'plural_title': _('Leaderboard'),
        'icon': 'users',
        # queryset is added in urls.py, can be specified in your settings as well
        'list': {
            'show_title': True,
            'per_line': 1,
            'add_button_subtitle': _('Create your account to join the community and be in the leaderboard!'),
            # default_ordering added in urls.py (level), can be specified in your settings as well
        },
        'add': {
            'alert_duplicate': False,
            'before_save': _accountBeforeSave,
            'redirect_after_add': _accountRedirectAfter,
        },
        'edit': {
            'redirect_after_edit': _accountRedirectAfter,
            'owner_only': True,
            'allow_delete': True,
            'redirect_after_delete': _accountRedirectAfterDelete,
        },
    }),
    ('user', {
        'title': _('Profile'),
        'plural_title': _('Players'),
        'navbar_link': False,
        'queryset': User.objects.all().select_related('preferences'),
        'item': {
            'js_files': ['bower/marked/lib/marked', 'profile'],
            'template': 'profile',
            'comments_enabled': False,
            'filter_queryset': _userItemFilterQuerySet,
            # extra_context added in urls.py (web.views.profileExtraContext), can be specified in your settings as well
        },
        'list': {
            'default_ordering': 'username',
            'per_line': 6,
            # filter_queryset added in urls.py (_userListFilterQuerySet), can be specified in your settings as well
        },
        'edit': {
            'staff_required': True,
            # form_class is added in urls.py (forms.Activity), can be specified in your settings as well
        }
    }),
    ('activity', {
        'title': _('Activity'),
        'pluaral_title': _('Activities'),
        'plural_name': 'activities',
        # queryset is added in urls.py, can be specified in your settings as well
        'navbar_link': False,
        'list': {
            'js_files': ['bower/marked/lib/marked'],
            'per_line': 1,
            'distinct': False,
            'add_button_subtitle': _('Share your adventures!'),
            'ajax_pagination_callback': 'updateActivities',
            'filter_queryset': _activitiesQuerysetWithLikesAndLiked,
            'no_result_template': 'include/activityFollowMessage',
            'default_ordering': '-modification',
        },
        'item': {
            'js_files': ['bower/marked/lib/marked'],
            'ajax_callback': 'updateActivities',
            'filter_queryset': _activitiesQuerysetWithLikesAndLiked,
        },
        'add': {
            'multipart': True,
            'alert_duplicate': False,
            'js_files': ['edit_activities'],
            # form_class is added in urls.py (forms.Activity), can be specified in your settings as well
        },
        'edit': {
            'multipart': True,
            'allow_delete': True,
            'js_files': ['edit_activities'],
        },
    }),
    ('notification', {
        'title': _('Notification'),
        'plural_title': _('Notifications'),
        # queryset is added in urls.py, can be specified in your settings as well
        'navbar_link': False,
        'list': {
            'show_title': True,
            'per_line': 1,
            'page_size': 5,
            'filter_queryset': _notificationsFilter,
            'default_ordering': 'seen',
            # extra_context is added in urls.py (to mark notifications as read), can be specified in your settings as well
        },
    }),
    ('report', {
        'navbar_link_list': 'more',
        'icon': 'fingers',
        # queryset is added in urls.py, can be specified in your settings as well
        'list': {
            'show_title': True,
            'staff_required': True,
            'per_line': 1,
            'js_files': ['reports'],
            'ajax_pagination_callback': 'updateReport',
            # filter_form is added in urls.py, can be specified in your settings as well
        },
        'item': {
            'comments_enabled': False,
            'owner_only': True,
            'js_files': ['reports'],
            'ajax_callback': 'updateReport',
        },
        'add': {
            'authentication_required': False,
            'alert_duplicate': False,
            'back_to_list_button': False,
            'types': {
                # form_class for each types are added in urls.py (forms.Activity), can be specified in your settings as well
                'activity': { 'title': _('Activity') },
                'account': { 'title': _('Account') },
                'user': { 'title': t['User'] },
            },
            'multipart': True,
        },
        'edit': {
            'multipart': True,
            'allow_delete': True,
            'redirect_after_delete': '/',
            'back_to_list_button': False,
        },
    })
])

############################################################
# Enabled pages

DEFAULT_ENABLED_PAGES = OrderedDict([
    ('index', {
        'custom': False,
        'title': t['Home'],
        'navbar_link': False,
    }),
    ('login', {
        'custom': False,
        'title': _('Login'),
        'navbar_link_list': 'you',
        'navbar_link_auth': (False, True),
    }),
    ('signup', {
        'custom': False,
        'title': _('Sign Up'),
        'navbar_link_list': 'you',
        'navbar_link_auth': (False, True),
    }),
    ('user', [
        {
            'custom': False,
            'title': _('Profile'),
            'icon': 'profile',
            'url_variables': [
                ('pk', '\d+', lambda (context): str(context['request'].user.id)),
                ('username', _usernameRegexp, lambda (context): context['request'].user.username),
            ],
            'navbar_link_list': 'you',
            'navbar_link_auth': (True, False),
        },
        {
            'custom': False,
            'title': _('Profile'),
            'url_variables': [('username', _usernameRegexp)],
            'navbar_link': False,
        },
    ]),
    ('settings', {
        'title': _('Settings'),
        'custom': False,
        'icon': 'settings',
        'navbar_link_list': 'you',
        'navbar_link_auth': (True, False),
    }),
    ('logout', {
        'custom': False,
        'title': _('Logout'),
        'icon': 'logout',
        'navbar_link_list': 'you',
        'navbar_link_auth': (True, False),
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
    ('about_game', {
        'ajax': True,
        'title': _('About the game'),
        'custom': False,
        'icon': 'about',
    }),
    ('donate', {
        'title': _('Donate'),
        'custom': False,
        'icon': 'heart',
        'navbar_link_list': 'more',
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
])
