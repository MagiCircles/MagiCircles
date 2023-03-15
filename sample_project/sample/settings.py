# -*- coding: utf-8 -*-
from django.conf import settings as django_settings
from sample import models

# Configure and personalize your website here.

############################################################
# License, game and site settings

SITE_NAME = 'Sample Website'
# SITE_EMOJIS = []
# SITE_DESCRIPTION = ''

GAME_NAME = 'Sample Game'
# GAME_URL = '/wiki/About%20Sample/'
# GAME_DESCRIPTION = u"""

COLOR = '#4a86e8'
# SECONDARY_COLOR = '#4a86e8'
# ACCENT_COLOR = '#4a86e8'

# LAUNCH_DATE = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

############################################################
# Images

SITE_IMAGE = 'sample.png'
# SITE_LOGO = 'sample_logo.png'
# SITE_NAV_LOGO = 'sample_nav_logo.png'
# SITE_LOGO_WHEN_LOGGED_IN = 'sample_logo_auth.png'
# EMAIL_IMAGE = 'sample_email.png'
# DONATE_IMAGE = 'mascot.png'
# ABOUT_PHOTO = 'staff.png'

# CORNER_POPUP_IMAGE = 'hi.png'
# CORNER_POPUP_IMAGE_OVERFLOW = True

############################################################
# Settings per languages

# SITE_NAME_PER_LANGUAGE = {
#     'ja': u'サンプル',
# }
# SITE_LOGO_PER_LANGUAGE = {
#     'ja': 'sample_logo_ja.png',
# }

############################################################
# Contact & Social

# CONTACT_EMAIL = 'contact@sample.com'
# CONTACT_REDDIT = 'db0company'
# CONTACT_FACEBOOK = 'sample'

# GITHUB_REPOSITORY = ('MagiCircles', 'Sample')

# TWITTER_HANDLE = 'sample'
# INSTAGRAM_HANDLE = 'sample'
# HASHTAGS = [u'SampleGame']

# FEEDBACK_FORM = u'https://forms.gle/3kLZMeeVKoYcAJHo7'

############################################################
# Homepage

# HOMEPAGE_BACKGROUND = 'background.png'
# HOMEPAGE_RIBBON = True

############################################################
# First steps

# FIRST_COLLECTION = 'card'
# GET_STARTED_VIDEO = 'FHkyH8Urero'

############################################################
# User preferences and profiles

# USER_COLORS = [
#     ('red', 'Red', 'red', '#ff4d5d'),
#     ('orange', 'Orange', 'orange', '#ffb054'),
#     ('yellow', 'Yellow', 'yellow', '#FFD34E'),
#     ('green', 'Green', 'green', '#54ff79'),
#     ('blue', 'Blue', 'blue', '#54b5ff'),
# ]

# DONATORS_STATUS_CHOICES = [
#     ('THANKS', 'Thanks'),
#     ('SUPPORTER', _('')),
#     ('LOVER', _('')),
#     ('AMBASSADOR', _('')),
#     ('PRODUCER', _('')),
#     ('DEVOTEE', _('')),
# ]

############################################################
# Activities

# MINIMUM_LIKES_POPULAR = 10

# ACTIVITY_TAGS = [
#     ('sample', _('Sample')),
#     ('idols', _('Idols')),
#     # Limited
#     ('SomeEvent', {
#         'translation': _('Happy event!'),
#         'start_date': datetime.datetime(2021, 11, 23, tzinfo=timezone.utc),
#         'end_date': datetime.datetime(2021, 12, 23, tzinfo=timezone.utc),
#     }),
# ] + DEFAULT_ACTIVITY_TAGS

############################################################
# Technical settings

SITE_URL = 'http://sample.com/'
SITE_STATIC_URL = '//i.sample.com/'

DISQUS_SHORTNAME = 'sample'
# GOOGLE_ANALYTICS = 'UA-59453399-5'

ACCOUNT_MODEL = models.Account
# FAVORITE_CHARACTERS_MODEL = models.Idol

############################################################
# Customize pages

# ENABLED_PAGES = DEFAULT_ENABLED_PAGES.copy()

############################################################
# Customize nav bar

# ENABLED_NAVBAR_LISTS = DEFAULT_ENABLED_NAVBAR_LISTS.copy()

# ENABLED_NAVBAR_LISTS['sample'] = {
#     'title': _('Sample'),
#     'icon': 'idolized',
# }

############################################################
# Seasons

# SEASONS = DEFAULT_SEASONS.copy()

# # Halloween theme

# SEASONS['halloween'].update({
#     'color': '#793698',
#     'secondary_color': '#E7C8FF',
#     'accent_color': '#C18EDA',
#     'theme': True,
#     'extracss_template': 'include/halloween_css.css',
#     'site_nav_logo': 'halloween/IdolStoryHalloweenLogo2021.png',
#     'site_logo': 'halloween/IdolStoryLogoHalloween.png',
#     'site_logo_when_logged_in': 'halloween/IdolStoryHorizontalLogoHalloween.png',
# })
