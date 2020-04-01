# -*- coding: utf-8 -*-
from collections import OrderedDict
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _, string_concat
from magi.django_translated import t
from magi.seasons import DEFAULT_SEASONS
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
    _('Loading'), _('No result.'),
    _('days'), _('hours'), _('minutes'), _('seconds'),
    _('Local time'),
    _('Copied'), _('Archived'), _('Unarchived'),
    _('End of new messages'),
    _('1st'), _('2nd'), _('3rd'),
    _('More'), _('Less'),
]

DEFAULT_JAVASCRIPT_TRANSLATED_TERMS = [
    'Loading', 'No result.',
    'You can\'t cancel this action afterwards.', 'Confirm', 'Cancel',
    'days', 'hours', 'minutes', 'seconds',
    'Local time',
    'Copied', 'Archived', 'Unarchived',
    'End of new messages',
    'More', 'Less',
]

############################################################

DEFAULT_CONTACT_DISCORD = 'https://discord.gg/mehDTsv'
DEFAULT_POEDITOR_URL = 'https://poeditor.com/join/project/h6kGEpdnmM'

DEFAULT_LANGUAGES_CANT_SPEAK_ENGLISH = ['ja', 'zh-hans', 'zh-hant', 'kr']

DEFAULT_SEASONS = DEFAULT_SEASONS

############################################################
# Groups

DEFAULT_GLOBAL_OUTSIDE_PERMISSIONS = {
    'Staff/Contributor Discord': { 'image': 'links/discord', 'url': DEFAULT_CONTACT_DISCORD },
    'Bug tracker': False, # Added in settings
    # 'Wiki editor' added in settings
}

DEFAULT_GROUPS = [
    ('manager', {
        'translation': _('Manager'),
        'description': 'The leader of our staff team is here to make sure that the website is doing well! They make sure we all get things done together and the website keeps getting new users everyday. They\'re also the decision maker in case of conflicts that can\'t be resolved via votes.',
        'permissions': [
            'edit_roles', 'edit_staff_status', 'edit_donator_status', 'see_profile_edit_button',
            'edit_staff_configurations', 'add_badges', 'see_collections_details',
            'manage_main_items', 'view_items_history',
            'edit_staff_details', 'moderate_reports', 'edit_reported_things', 'post_community_event_activities',
            'apply_suggestions',
            'message_almost_anyone',
            'manage_prizes', 'manipulate_activities', 'mark_activities_as_staff_pick',
            'edit_activities_post_language', 'order_by_any_field',
            'list_homepage_arts',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'outside_permissions': {
            'Tweetdeck': { 'image': 'links/twitter', 'url': 'https://tweetdeck.twitter.com/' },
            'Disqus moderation': False, # Added in settings
        },
        'requires_staff': True,
        'guide': '/help/Managers%20guide',
    }),
    ('circles_manager', {
        'translation': string_concat('Circles - ', _('Manager')),
        'description': 'Supervises and helps the creation and growth of all the websites. Advises but generally doesn\'t interfere with the managers\' decisions.',
        'requires_staff': True,
        'permissions': [
            'has_twitter_password',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'guide': '/help/Circles%20managers%20guide',
    }),
    ('team', {
        'translation': _('Team manager'),
        'description': 'Knows all the team members and discuss with them on a regular basis to make sure they are all active. Ensures that the staff team is only composed of active members, keep track of members who are taking a break, regularly check with members if they\'re still interested, and help members retire if they want to. They are also in charge of assigning and revoking most permissions.',
        'permissions': [
            'edit_staff_status', 'edit_roles', 'see_profile_edit_button', 'edit_staff_details',
            'order_by_any_field',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'outside_permissions': {
            'Administrate the contributors on GitHub': False, # Added in settings
            'Administrate the contributors on Tweetdeck': {
                'image': 'links/twitter',
                'url': 'https://tweetdeck.twitter.com/',
            },
            'Administrate the moderators on Disqus': False, # Added in settings
        },
        'guide': '/help/Team%20managers%20guide',
    }),
    ('finance', {
        'translation': _('Finance manager'),
        'description': 'Keeps track of our monthly spending and donations, makes sure donators get their rewards, and we have enough funds every month to cover the server and other expenses.',
        'permissions': [
            'add_donation_badges',
            'manage_donation_months',
            'edit_donator_status',
            'message_almost_anyone',
        ],
        'requires_staff': True,
        'requires_staff': True,
        'outside_permissions': {
            'Patreon manager': { 'icon': 'heart', 'url': 'https://www.patreon.com/manageRewards' },
            'Donators forms responses': {
                'icon': 'icons-list',
                'url': 'https://docs.google.com/spreadsheets/d/18yFRsk3JpM-lIwT-Gp7teXVpliPgzBP7Lq2T7F6LJjk/edit',
            },
            'Monthly prizes': {
                'icon': 'present',
                'url': 'https://docs.google.com/spreadsheets/d/1Ocv1uDoqlC_4ffg1SUQKLv1Xjd9H84Qg-YYhzh4WH7Q/edit',
            },
            'Budget sheet': {
                'icon': 'money',
                'url': 'https://docs.google.com/spreadsheets/d/18dwZyE37SKFRXDG3hWd7O7JpQv41CSINg_904S96T1M/edit',
            },
        },
        'guide': '/help/Finance%20managers%20guide',
    }),
    ('db', {
        'translation': _('Database maintainer'),
        'description': 'We gather all the game data in one convenient place for you! Our database maintainers manually update the details as soon as they are available.',
        'permissions': [
            'manage_main_items', 'translate_items',
            'order_by_any_field',
            'list_homepage_arts',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'guide': '/help/Database%20maintainers%20guide',
    }),
    ('dbapi', {
        'translation': string_concat(_('Database maintainer'), ' (API)'),
        'description': 'Extracts assets and data and automatically updates our website. They do their best to publish all the details as soon they are available.',
        'permissions': [
            'manage_main_items',
            'order_by_any_field',
            'list_homepage_arts',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'outside_permissions': {
            'API key': {
                'icon': 'developer',
                'url': '/o/applications/',
            },
        },
        'guide': '/help/Database%20maintainers%20guide',
    }),
    ('cm', {
        'translation': _('Community manager'),
        'description': 'We got you covered with all the game news on the website! Thanks to our active team, you know that by following our latest activities, you\'ll never miss anything!',
        'permissions': [
            'post_news',
            'edit_staff_configurations',
            'access_site_before_launch',
            'beta_test_features',
            'message_almost_anyone',
        ],
        'requires_staff': True,
        'stats': [
            {
                'model': 'Activity',
                'filters': { 'c_tags__icontains': '"staff"' },
                'template': _('Posted {total} news'),
            },
        ],
        'guide': '/help/Community%20managers%20guide',
    }),
    ('twitter_cm', {
        'translation': string_concat(_('Community manager'), ' (', _('Twitter'), ')'),
        'description': 'We got you covered with all the game news on Twitter! Thanks to our active team, you know that by following us on Twitter, you\'ll never miss anything!',
        'requires_staff': True,
        'permissions': [
            'post_on_twitter',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'outside_permissions': {
            'Tweetdeck': { 'image': 'links/twitter', 'url': 'https://tweetdeck.twitter.com/' },
        },
        'guide': '/help/Community%20managers%20guide',
    }),
    ('instagram_cm', {
        'translation': string_concat(_('Community manager'), ' (Instagram)'),
        'description': 'We got you covered with all the game news on Instagram! Thanks to our active team, you know that by following us on Instagram, you\'ll never miss anything!',
        'requires_staff': True,
        'permissions': [
            'post_on_instagram',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'outside_permissions': {
            'Instagram account': { 'image': 'links/instagram', 'url': 'https://instagram.com/' },
        },
        'guide': '/help/Community%20managers%20guide',
    }),
    ('external_cm', {
        'translation': _('External communication'),
        'description': 'We\'re very active on other social media, such as Facebook, reddit and various forums! Our team will take the time to inform the other community about our website news and hopefully get more users from there, as well as valuable feedback to improve the website!',
        'requires_staff': True,
        'permissions': [
            'access_site_before_launch',
            'beta_test_features',
        ],
        'guide': '/help/External%20communication%20guide',
    }),
    ('support', {
        'translation': _('Support'),
        'description': 'Need help with our website or the game? Our support team is here to help you and answer your questions!',
        'requires_staff': True,
        'permissions': [
            'access_site_before_launch',
            'beta_test_features',
            'message_almost_anyone',
        ],
        'outside_permissions': {
            'Tweetdeck': { 'image': 'links/twitter', 'url': 'https://tweetdeck.twitter.com/' },
            'Receive private messages on Facebook': False, # Added in settings
            'Receive private messages on Reddit': False, # Added in settings
            'Receive emails': { 'icon': 'contact', 'url': u'mailto:{}'.format(django_settings.AWS_SES_RETURN_PATH) },
            # 'Feedback form' added in settings if exists
        },
        'guide': '/help/Support%20guide',
    }),
    ('a_moderator', {
        'translation': string_concat(_('Moderator'), ' (', _('Active'), ')'),
        'description': 'We want all of our users of all ages to have a pleasant a safe stay in our website. That\'s why our team of moderators use the website everyday and report anything that might be inappropriate or invalid!',
        'permissions': [
            'see_profile_edit_button',
            'edit_activities_post_language',
            'manipulate_activities',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'stats': [
            {
                'model': 'Report',
                'template': _('Submitted {total} reports'),
            },
        ],
        'guide': '/help/Moderators%20guide',
    }),
    ('d_moderator', {
        'translation': string_concat(_('Moderator'), ' (', _('Decisive'), ')'),
        'description': 'When something gets reported, our team of decisive moderators will make a decision on whether or not it should be edited or deleted. This 2-steps system ensures that our team makes fair decisions!',
        'permissions': [
            'moderate_reports',
            'edit_reported_things',
            'manipulate_activities',
            'edit_activities_post_language',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'outside_permissions': {
            'Disqus moderation': False, # Added in settings
        },
        'stats': [
            {
                'model': 'Report',
                'selector_to_owner': 'staff',
                'filters': { 'i_status__in': [1, 2] },
                'template': _('Edited or deleted {total} reported items'),
            },
        ],
        'guide': '/help/Moderators%20guide',
    }),
    ('entertainer', {
        'translation': _('Community entertainer'),
        'description': 'We keep the community active and happy by organizing fun stuff: contests, giveaways, games, etc. We\'re open to feedback and ideas!',
        'permissions': [
            'post_news',
            'message_almost_anyone',
            'edit_staff_configurations',
            'add_badges',
            'post_community_event_activities',
            'add_prizes',
            'manipulate_activities',
            'mark_activities_as_staff_pick',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': True,
        'outside_permissions': {
            'Tweetdeck': { 'image': 'links/twitter', 'url': 'https://tweetdeck.twitter.com/' },
        },
        'stats': [
            {
                'model': 'Activity',
                'filters': { 'c_tags__icontains': '"news"' },
                'template': _('Organized and posted about {total} community events'),
            },
        ],
        'guide': '/help/Community%20entertainers%20guide',
    }),
    ('assistant', {
        'translation': _('Backup staff'),
        'description': 'Our super heroes, magicians and jack-of-all-trades. There\'s nothing they can\'t do! We call them to the rescue whenever something needs to get done and they quickly and efficiently help our website and community.',
        'requires_staff': True,
        'permissions': [
            'access_site_before_launch',
            'beta_test_features',
        ],
        'guide': '/help/Backup%20staff%20guide',
    }),
    ('discord', {
        'translation': string_concat(_('Moderator'), ' (Discord)'),
        'description': 'Help keep Circle\'s private server well organized and fun for all our staff and contributors.',
        'requires_staff': False,
        'outside_permissions': {
            'Discord moderation': { 'image': 'links/discord', 'url': DEFAULT_CONTACT_DISCORD },
        },
        'guide': '/help/Discord%20moderators%20guide',
    }),
    ('translator', {
        'translation': _('Translator'),
        'description': 'Many people can\'t understand English very well, so by doing so our amazing translators work hard to translate our websites in many languages. By doing so they\'re helping hundreds of people access the information we provide easily and comfortably.',
        'permissions': [
            'translate_items',
            'translate_staff_configurations',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': False,
        'outside_permissions': {
            'POEditor': { 'icon': 'link', 'url': DEFAULT_POEDITOR_URL },
        },
        'guide': '/help/Translators%20guide',
        'settings': ['languages'],
    }),
    ('design', {
        'translation': _('Graphic designer'),
        'description': 'Our graphic designers help with banners, flyers, or any other graphic edit we need to communicate about the website or organize special events.',
        'requires_staff': False,
        'guide': '/help/Join%20the%20graphic%20design%20team',
    }),
    ('artist', {
        'translation': _('Artist'),
        'description': 'Our artists help with illustrations and drawings we need to communicate about the website or organize special events.',
        'requires_staff': False,
        'guide': '/help/Join%20the%20graphic%20design%20team',
    }),
    ('developer', {
        'translation': _('Developer'),
        'description': 'Developers contribute to the website by adding new features or fixing bugs, and overall maintaining the website.',
        'permissions': [
            'advanced_staff_configurations',
            'see_collections_details',
            'order_by_any_field',
            'list_homepage_arts',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': False,
        'guide': '/help/Developers%20guide',
    }),
    ('sysadmin', {
        'translation': _('System administrator'),
        'description': 'Our system administrators take care of the infrasturcture of our websites, including maintaining the servers, deploying new versions, ensuring that we scale according to traffic and under budget, and overall instrastructure monitoring.',
        'permissions': [
            'advanced_staff_configurations',
            'see_profile_edit_button',
            'mark_email_addresses_invalid',
            'see_collections_details',
            'order_by_any_field',
            'access_site_before_launch',
            'beta_test_features',
        ],
        'requires_staff': False,
        'guide': '/help/System%30administrator%20guide',
    }),
    ('betatester', {
        'translation': _(u'β-tester'),
        'description': 'Beta testers have access to features before everybody else!',
        'permissions': [
            'access_site_before_launch',
            'beta_test_features',
        ],
    }),
    ('betatester_donator', {
        'translation': string_concat(_(u'β-tester'), ' (', _('Donators'), ')'),
        'description': 'Beta testers have access to features before everybody else!',
        'permissions': [
            'access_site_before_launch',
            'beta_test_features',
        ],
    }),
]

############################################################
# Navbar lists

DEFAULT_ENABLED_NAVBAR_LISTS = OrderedDict([
    ('you', {
        'title': lambda context: context['request'].user.username if context['request'].user.is_authenticated() else _('You'),
        'icon': 'profile',
        'order': ['user', 'privatemessage_list', 'settings', 'logout', 'login', 'signup'],
    }),
    ('staff', {
        'title': 'Staff',
        'icon': 'staff',
    }),
    ('more', {
        'title': '',
        'icon': 'more',
        'order': [
            'about',
            'about_game',
            'donate_list',
            'help',
            'map',
            'staffdetails_list',
            'report_list',
            'badge_list',
            'staffconfiguration_list',
            'collections',
        ],
    }),
])

############################################################
# Activities

DEFAULT_HOME_ACTIVITY_TABS = OrderedDict([
    ('popular', {
        'title': _('Popular'),
        'icon': 'statistics',
        'form_fields': {
        },
    }),
    ('hot', {
        'title': _('Hot'),
        'icon': 'fire',
        'form_fields': {
            'is_popular': None,
        },
    }),
    ('new', {
        'title': _('New'),
        'icon': 'new',
        'form_fields': {
            'is_popular': None,
            'ordering': 'creation',
        },
    }),
    ('following', {
        'title': _('Following'),
        'icon': 'users',
        'form_fields': {
            'is_popular': None,
            'is_following': True,
        },
    }),
    ('staffpicks', {
        'title': _('Staff picks'),
        'icon': 'heart',
        'form_fields': {
            'is_popular': None,
            'c_tags': ['staff'],
        },
    }),
])

DEFAULT_ACTIVITY_TAGS = [
    # Community
    ('introduction', _('Introduce yourself')),
    ('comedy', _('Comedy')),
    ('meme', _('Meme')),
    ('cosplay', _('Cosplay')),
    ('fanart', _('Fanart')),
    ('edit', _('Graphic edit')),
    ('merch', _('Merchandise')),
    ('community', _('Community')),
    ('question', _('Question')),

    # Restricted
    ('news', {
        'translation': _('News'),
        'has_permission_to_add': lambda r: (
            r.user.is_staff and r.user.hasPermission('post_news')),
    }),
    ('staff', {
        'translation': _('Staff picks'),
        'has_permission_to_add': lambda r: (
            r.user.is_staff and r.user.hasPermission('mark_activities_as_staff_pick')),
    }),

    # Meta
    ('unrelated', None), # set in settings.py
    ('swearing', _('Swearing')),
    ('questionable', {
        'translation': _('Questionable'),
    }),
    ('nsfw', {
        'translation': _('NSFW'),
        'hidden_by_default': True,
        'has_permission_to_show': lambda r: u'{} {}'.format(
            _('You need to be over 18 years old.'),
            (_('You can change your birthdate in your settings.')
             if not r.user.preferences.age else u''),
        ) if r.user.is_authenticated() and r.user.preferences.age < 18
        else True,
    }),
]

############################################################
# Enabled pages

DEFAULT_ENABLED_PAGES = OrderedDict([
    ('index', {
        'custom': False,
        'enabled': False,
        'navbar_link': False,
        'boilerplate': False,
    }),
    ('login', {
        'custom': False,
        'title': _('Login'),
        'navbar_link_list': 'you',
        'logout_required': True,
        'boilerplate': False,
    }),
    ('signup', {
        'custom': False,
        'title': _('Sign Up'),
        'navbar_link_list': 'you',
        'logout_required': True,
        'as_form': True,
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
        'full_template': True,
    }),
    ('logout', {
        'custom': False,
        'title': _('Logout'),
        'icon': 'logout',
        'navbar_link_list': 'you',
        'authentication_required': True,
        'boilerplate': False,
    }),
    ('about', [
        # page_description set in settings.py
        {
            'title': lambda _c: _('About {thing}').format(thing=_c['t_site_name']),
            'custom': False,
            'icon': 'about',
            'navbar_link_list': 'more',
            'comments_enabled': True,
        },
        {
            'ajax': True,
            'title': lambda _c: _('About {thing}').format(thing=_c['t_site_name']),
            'custom': False,
            'icon': 'about',
        },
    ]),
    ('prelaunch', {
        'title': _('Coming soon'),
        'custom': False,
        'navbar_link': False,
    }),
    ('about_game', [
        # page_description set in settings.py
        {
            'title': lambda _c: _('About {thing}').format(thing=_c['t_game_name']),
            'custom': False,
            'icon': 'about',
            'navbar_link_list': 'more',
            'logout_required': True,
        },
        {
            'ajax': True,
            'title': lambda _c: _('About {thing}').format(thing=_c['t_game_name']),
            'custom': False,
            'icon': 'about',
        },
    ]),
    ('map', {
        'title': _('Map'),
        'custom': False,
        'icon': 'map',
        'navbar_link_list': 'more',
        'full_template': True,
        # page_description set in settings.py
    }),
    ('help', [
        # page_description set in settings.py
        {
            'custom': False,
            'title': _('Help'),
            'icon': 'help',
            'navbar_link_list': 'more',
            'template': 'wiki',
            'sidebar_template': 'wiki_sidebar',
            'as_sidebar': True,
            'show_title': True,
        },
        {
            'custom': False,
            'title': _('Help'),
            'url_variables': [
                ('wiki_url', '[^/]+'),
            ],
            'navbar_link': False,
            'template': 'wiki',
            'sidebar_template': 'wiki_sidebar',
            'as_sidebar': True,
            'show_title': True,
        },
    ]),
    ('wiki', [
        # page_description set in settings.py
        {
            'enabled': False,
            'custom': False,
            'title': _('Wiki'),
            'icon': 'wiki',
            'check_permissions': lambda c: c['request'].LANGUAGE_CODE not in DEFAULT_LANGUAGES_CANT_SPEAK_ENGLISH,
            'as_sidebar': True,
            'show_title': True,
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
            'check_permissions': lambda c: c['request'].LANGUAGE_CODE not in DEFAULT_LANGUAGES_CANT_SPEAK_ENGLISH,
            'as_sidebar': True,
            'show_title': True,
        },
    ]),
    ('block', {
        'navbar_link': False,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_form': True,
    }),
    ('check_activities_in_wrong_language', {
        'title': 'Check activities in wrong language',
        'redirect': u'/activities/?is_popular=1&i_language={}&ordering=creation&reverse_order=on&fix_language'.format(
            u','.join([str(l) for l in dict(django_settings.LANGUAGES).keys() if l != 'en']),
        ),
        'navbar_link_list': 'staff',
        'icon': 'checked',
        'permissions_required': ['edit_activities_post_language'],
    }),
    ('translations', {
        'title': 'Translations',
        'custom': False,
        'navbar_link_list': 'staff',
        'icon': 'translate',
        'permissions_required': ['translate_items'],
        'show_title': True,
    }),
    ('translations_duplicator', [
        {
            'title': 'Translations duplicator',
            'custom': False,
            'icon': 'translate',
            'permissions_required': ['translate_items'],
            'navbar_link': False,
            'url_variables': [
                ('model_name', '[a-z]+'),
                ('field_name', '[a-z_]+'),
                ('language', '[a-z]+'),
            ],
            'show_title': True,
        },
        {
            'title': 'Translations duplicator',
            'custom': False,
            'icon': 'translate',
            'permissions_required': ['translate_items'],
            'navbar_link': False,
            'url_variables': [
                ('collection_name', '[a-z]+'),
                ('field_name', '[a-z_]+'),
            ],
            'show_title': True,
        },
    ]),
    ('collections', {
        'title': 'Collections',
        'custom': False,
        'navbar_link_list': 'staff',
        'icon': 'developer',
        'permissions_required': ['see_collections_details'],
        'show_title': True,
    }),
    ('translations_check', {
        'title': 'POEditor translations term checker',
        'custom': False,
        'navbar_link_list': 'staff',
        'icon': 'developer',
        'permissions_required': ['translate_items'],
        'as_form': True,
    }),
    ('homepage_arts', {
        'title': 'Homepage previews',
        'custom': False,
        'navbar_link_list': 'staff',
        'icon': 'home',
        'one_of_permissions_required': ['list_homepage_arts'],
    }),
    ('sitemap', {
        'title': _('Sitemap'),
        'custom': False,
        'navbar_link': False,
        'icon': 'category',
    }),
    ('deletelink', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'as_json': True,
        'authentication_required': True,
        # always returns None
    }),
    ('likeactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('archiveactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('unarchiveactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('bumpactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('drownactivity', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('markactivitystaffpick', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('removeactivitystaffpick', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('pk', '\d+'),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('follow', {
        'ajax': True,
        'custom': False,
        'url_variables': [
            ('username', _usernameRegexp),
        ],
        'authentication_required': True,
        'as_json': True,
    }),
    ('twitter_avatar', {
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('twitter', '[^/]+'),
        ],
        'boilerplate': False,
        # always redirects
    }),
    ('changelanguage', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'boilerplate': False,
        'authentication_required': True,
    }),
    ('markallnotificationsread', {
        'custom': False,
        'navbar_link': False,
        'boilerplate': False,
        'authentication_required': True,
        # always redirects
    }),
    ('me', {
        'custom': False,
        'navbar_link': False,
        'boilerplate': False,
        'authentication_required': True,
        # always redirects
    }),
    ('moderatereport', {
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('report', '\d+'),
            ('action', '\w+'),
        ],
        'boilerplate': False,
        'permissions_required': ['moderate_reports'],
    }),
    ('whatwillbedeleted', {
        'title': _('Confirm'),
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('thing', '.+'),
            ('thing_id', '\d+'),
        ],
    }),
    ('reportwhatwillbedeleted', {
        'title': _('Confirm'),
        'ajax': True,
        'custom': False,
        'navbar_link': False,
        'url_variables': [
            ('report', '\d+'),
        ],
        'permissions_required': ['moderate_reports'],
        'template': 'whatwillbedeleted',
    }),
    ('successedit', [
        {
            'title': _('Successfully edited!'),
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
        {
            'title': _('Successfully edited!'),
            'ajax': True,
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
    ]),
    ('successadd', [
        {
            'title': _('Successfully added!'),
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
        {
            'title': _('Successfully added!'),
            'ajax': True,
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
    ]),
    ('successdelete', [
        {
            'title': _('Successfully deleted!'),
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
        {
            'title': _('Successfully deleted!'),
            'ajax': True,
            'custom': False,
            'navbar_link': False,
            'template': 'success',
            'show_small_title': False,
        },
    ]),

    # Seasonal
    ('adventcalendar', [
        {
            'title': _('Advent calendar'),
            'custom': False,
            'authentication_required': True,
            'navbar_link': False,
        },
        {
            'title': _('Advent calendar'),
            'custom': False,
            'authentication_required': True,
            'navbar_link': False,
            'url_variables': [
                ('day', '\d+'),
            ],
        },
        {
            'title': _('Advent calendar'),
            'ajax': True,
            'custom': False,
            'authentication_required': True,
        },
        {
            'title': _('Advent calendar'),
            'ajax': True,
            'custom': False,
            'authentication_required': True,
            'url_variables': [
                ('day', '\d+'),
            ],
        },
    ]),
    ('endaprilfool', {
        'ajax': True,
        'authentication_required': True,
        'custom': False,
        'as_json': True,
    }),
])

############################################################
# Default profile tabs

DEFAULT_PROFILE_TABS = OrderedDict([
    ('account', {
        'name': _('Accounts'),
        'icon': 'game',
    }),
    ('badge', {
        'name': _('Badges'),
        'icon': 'badge',
        'callback': 'loadBadges',
    }),
])

############################################################
# Default navbar ordering

DEFAULT_NAVBAR_ORDERING = [
    'account_list',
    'staff',
    'you',
    'more',
]

############################################################
# Default prelaunch enabled pages

DEFAULT_PRELAUNCH_ENABLED_PAGES = [
    'index',
    'login',
    'logout',
    'signup',
    'prelaunch',
    'about',
    'about_game',
    'donate_list',
    'changelanguage',
    'help',
]

############################################################
# Default extra preferences

DEFAULT_EXTRA_PREFERENCES = [
    ('background', _('Background')),
]

############################################################
# Default homepage art position

DEFAULT_HOMEPAGE_ART_POSITION = {
    'position': 'center center',
    'size': 'cover',
    'y': 'center',
    'x': 'center',
}
