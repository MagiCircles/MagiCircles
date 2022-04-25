from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _, string_concat
from test import models

SITE_NAME = 'Sample Website'
SITE_URL = 'http://test.com/'
SITE_IMAGE = 'test.png'
SITE_STATIC_URL = '//localhost:{}/'.format(django_settings.DEBUG_PORT) if django_settings.DEBUG else '//i.test.com/'
GAME_NAME = 'Sample Game'
DISQUS_SHORTNAME = 'test'
ACCOUNT_MODEL = models.Account
COLOR = '#4a86e8'

GROUPS = [
    ('manager', {
        'translation': _('Manager'),
        'description': 'The leader of our staff team is here to make sure that the website is doing well! They make sure we all get things done together and the website keeps getting new users everyday.',
        'permissions': ['edit_roles', 'edit_staff_status', 'edit_donator_status', 'see_profile_edit_button', 'edit_staff_configurations', 'add_badges'],
        'requires_staff': True,
    }),
    ('team', {
        'translation': _('Team manager'),
        'description': 'Knows all the team members and discuss with them on a regular basis to make sure they are all active.',
        'permissions': ['edit_staff_status', 'edit_roles', 'see_profile_edit_button'],
        'requires_staff': True,
    }),
    ('finance', {
        'translation': _('Finance manager'),
        'description': 'The finances manager keeps track of our monthly spending and donations, makes sure donators get their rewards, and we have enough funds every month to cover the server and other expenses.',
        'permissions': ['add_donation_badges', 'manage_donation_months', 'edit_donator_status'],
        'requires_staff': True,
    }),
    ('db', {
        'translation': _('Database maintainer'),
        'description': 'We gather all the game data in one convenient place for you~ Some of our team members extract the assets and data directly from the game, some enter missing info manually. We do our best to publish all the game data as soon as it gets published!',
        'permissions': ['manage_main_items'],
        'requires_staff': True,
    }),
    ('cm', {
        'translation': _('Community manager'),
        'description': 'We got you covered with all the game news on the website! Thanks to our active team, you know that by following our latest activities, you\'ll never miss anything!',
        'permissions': ['edit_staff_configurations'],
        'requires_staff': True,
    }),
    ('twitter_cm', {
        'translation': string_concat(_('Community manager'), ' (', _('Twitter'), ')'),
        'description': 'We got you covered with all the game news on Twitter! Thanks to our active team, you know that by following us on Twitter, you\'ll never miss anything!',
        'requires_staff': True,
    }),
    ('external_cm', {
        'translation': _('External communication'),
        'description': 'We\'re very active on other social media, such as Facebook, reddit and various forums! Our team will take the time to inform the other community about our website news and hopefully get more users from there, as well as valuable feedback to improve the website!',
        'requires_staff': True,
    }),
    ('support', {
        'translation': _('Support'),
        'description': 'Need help with our website or the game? Our support team is here to help you and answer your questions!',
        'requires_staff': True,
    }),
    ('a_moderator', {
        'translation': string_concat(_('Moderator'), ' (', _('Active'), ')'),
        'description': 'We want all of our users of all ages to have a pleasant a safe stay in our website. That\'s why our team of moderators use the website everyday and report anything that might be inappropriate or invalid!',
        'requires_staff': True,
    }),
    ('d_moderator', {
        'translation': string_concat(_('Moderator'), ' (', _('Decisive'), ')'),
        'description': 'When something gets reported, our team of decisive moderators will make a decision on whether or not it should be edited or deleted. This 2-steps system ensures that our team makes fair decisions!',
        'permissions': ['moderate_reports', 'edit_reported_things'],
        'requires_staff': True,
    }),
    ('entertainer', {
        'translation': _('Community entertainer'),
        'description': 'We keep the community active and happy by organizing fun stuff: contests, giveaways, games, etc. We\'re open to feedback and ideas!',
        'permissions': ['edit_staff_configurations', 'add_badges'],
        'requires_staff': True,
    }),
    ('translator', {
        'translation': _('Translator'),
        'description': 'Many people can\'t understand English very well, so by doing so our amazing translators work hard to translate our websites in many languages. By doing so they\'re helping hundreds of people access the information we provide easily and comfortably.',
        'permissions': ['translate_items', 'translate_staff_configurations'],
        'requires_staff': False,
    }),
    ('design', {
        'translation': _('Graphic designer'),
        'description': 'Our graphic designers help with banners, flyers, or any other graphic edit we need to communicate about the website or organize special events.',
        'requires_staff': False,
    }),
    ('artist', {
        'translation': _('Artist'),
        'description': 'Our artists help with illustrations and drawings we need to communicate about the website or organize special events.',
        'requires_staff': False,
    }),
    ('developer', {
        'translation': _('Developer'),
        'description': 'Developers contribute to the website by adding new features or fixing bugs, and overall maintaining the website.',
        'permissions': ['advanced_staff_configurations'],
        'requires_staff': False,
    }),
    ('sysadmin', {
        'translation': _('System administrator'),
        'description': 'Our system administrators take care of the infrasturcture of our websites, including maintaining the servers, deploying new versions, ensuring that we scale according to traffic and under budget, and overall instrastructure monitoring.',
        'permissions': ['advanced_staff_configurations', 'manage_main_items'],
        'requires_staff': False,
    }),
]
