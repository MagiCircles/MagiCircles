# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _, string_concat

# Will be added to the context directly
CONTEXT_SETTINGS = [
    # CSS file that will be included within the HTML in <style>. Useful when including static files.
    'extracss_template',

    # Logo in the navbar. Can be a full URL or partial.
    'site_nav_logo',

    # Logo on the homepage. Can be a full URL or partial.
    'site_logo',

    # Javascript that will be included within the HTML.
    'extrajavascript',
]

# Will generate a separate stylesheet
CSS_SETTINGS = [
    # Colors
    'color',
    'secondary_color',
    'accent_color',
    # When set to True, will load {season}.less
    'theme',
]

# All valid settings that will be cached in generated_settings.py for current season(s)
AVAILABLE_SETTINGS = CONTEXT_SETTINGS + CSS_SETTINGS + [
    'ajax_callback',
    'js_variables',
    'to_context',
    'to_random_homepage_art',
    'to_random_homepage_background',
    'extra',
]

# Can be changed from the Staff Configurations page
# More can be added via "staff_configurations_settings"
STAFF_CONFIGURATIONS_SETTINGS = [
    'site_nav_logo',
    'site_logo',
    'extracss',
    'extrajavascript',
    'activity_tag_banner',
]

DEFAULT_SEASONS = {
    'newyear': {
        'start_date': (12, 31),
        'end_date': (01, 02),
        'activity_tag': string_concat(_('Happy New Year!'), u' 🍾🎆'),
    },
    'chinesenewyear': {
        'start_date': (01, 21),
        'end_date': (02, 18),
        'activity_tag': string_concat(_('Happy Lunar New Year!'), u' 🐉🧨🧧'),
    },
    'valentines': {
        'start_date': (02, 13),
        'end_date': (02, 15),
        'activity_tag': string_concat(_('Happy Valentine\'s Day!'), u' 💝🍫'),
    },
    'leapday': {
        'start_date': (02, 29),
        'end_date': (03, 01),
        'activity_tag': string_concat(_('Happy Leap Day!'), u' 🐸'),
    },
    'pieday': {
        'start_date': (03, 14),
        'end_date': (03, 15),
        'activity_tag': string_concat(_('Happy Pi Day!'), u' π🥧'),
    },
    'whiteday': {
        'start_date': (03, 13),
        'end_date': (03, 16),
        'activity_tag': string_concat(_('Happy White Day!'), u'🍬🎁')
    },
    'stpatrick': {
        'start_date': (03, 17),
        'end_date': (03, 18),
        'activity_tag': string_concat(_('Happy St Patrick\'s Day!'), u' ☘🇮🇪'),
    },
    'aprilfools': {
        'start_date': (03, 31),
        'end_date': (04, 03),
        'activity_tag': string_concat(_('Happy April Fool\'s Day!'), u' 🤪😜🤣'),
        'extrajavascript': 'aprilFools();',
        'extra': {
            'badge_image': 'https://i.imgur.com/lwhrjSx.png',
        },
        'js_variables': {
            'aprilfools_configuration': {
                'items': [
                    'https://i.imgur.com/c9A5t9K.png',
                    'https://i.imgur.com/jpxoP2F.png',
                    'https://i.imgur.com/PixI1iT.png',
                    'https://i.imgur.com/SFeAvQQ.png',
                    'https://i.imgur.com/Jv1TE50.png',
                ],
                'startImage': 'https://i.imgur.com/ccQhmou.png',
                'bubbleColor': '#3AD7FF',
                'startBubbleText': '<h1>April Fools!</h1><p>Celebrate April Fool this spring with a fun Easter egg hunt on {site_name}!</p>',
                'startText': u'If you manage to finish before the end of April 1st, you\'ll earn a badge! 🏅',
                'startButton': 'Find all the <img src="https://i.imgur.com/c9A5t9K.png"/> eggs!',
                'endBubbleText': u'Congratulations 🎉<br>You found all the <img src="https://i.imgur.com/c9A5t9K.png"/> eggs!',
                'endText': 'We hope you had fun!',
                'afterBadgeText': 'To thank you for joining the fun, you just received a badge!',
                'endImage': 'https://i.imgur.com/ccQhmou.png',
                'hiddenAfterDivs': [
                    ['.home-site-donate-message .btn', 'Donators are the reason our community thrive!'],
                    ['#alternative-donations a.btn', 'Donations help the community thrive!'],
                    ['[data-item="donate"] .donate-month', 'Donations help the community thrive!'],
                    ['[data-cuteform-val="tr"]', 'We are an international community. Try to change your language!'],
                    ['[for="id_c_tags_12"]', 'You can look for activities with tags! So many to choose from...'],
                    ['#id_search', 'Searching and filtering is fun!'],
                    ['#filter-form-presets h4', 'If you don\'t know what to look for, you can check our suggestions!'],
                    ['.btn-group.writecomments', 'Leave comments on your friends posts!'],
                    ['#disqus_thread', 'Leave comments!'],
                    ['[data-item="account"] div', 'Have you checked the leaderboard?'],
                    ['.page-title-account_list [class^="flaticon"]', 'Have you checked the leaderboard?'],
                    ['body.current-notification_list h1', 'Have you received any notifications lately?'],
                    ['[for="id_i_message"]', 'Notifications are searchable!'],
                    ['.current-about #staff', 'Have you met our staff team?'],
                    ['.current-about main .container [href^="https://facebook.com/"]', 'You can contact us on Facebook~'],
                    ['.current-about #icons', 'Check out our about page!'],
                    ['.current-about #developers', 'Check out our about page!'],
                    ['.current-about #contributors', 'We have contributors helping the staff team. Make sure you meet them all!'],
                    ['.follow-buttons', 'Have you checked your profile?'],
                    ['.text-right.badges a', 'Have you checked your profile?'],
                    ['.staff-status', 'Our staff team would love to have more followers~'],
                    ['.current-privatemessage_list h1', 'Have you received any private message lately?'],
                    ['[name="d_hidden_tags-cosplay"]', 'Did you know you can hide and show tagged activities? Check your activities settings!'],
                    ['#form [class^=flaticon-]', 'Check your settings!'],
                    ['.glyphicon.glyphicon-chevron-up', 'Check your settings!'],
                    ['#wiki-title', 'We have a really cool wiki!'],
                    ['#wiki-content', 'We have really cool help pages!'],
                    ['#wiki-sidebar', 'We have a really cool wiki!'],
                    ['.navbar-brand', 'Check the navbar!'],
                    ['[data-link-name="more"] .dropdown-header', 'Have you checked out our other website from the "..." top bar?'],
                    ['.page-title-map', 'Check the map of players!'],
                ],
            },
        },
    },
    'easter': {
        'start_date': (03, 22),
        'end_date': (04, 26),
        'activity_tag': string_concat(_('Happy Easter!'), u' 🐰🥚🍫🐣'),
    },
    'may4': {
        'start_date': (05, 04),
        'end_date': (05, 06),
        'activity_tag': _('May the Fourth be with you!'),
    },
    'cincodemayo': {
        'start_date': (05, 05),
        'end_date': (05, 06),
        'activity_tag': string_concat(_('Happy Cinco de Mayo!'), u' 🇲🇽'),
    },
    'pride': {
        'start_date': (06, 01),
        'end_date': (07, 01),
        'activity_tag': string_concat(_('Happy Pride Month!'), u' 🏳️‍🌈🏳️‍⚧️'),
    },
    'thanksgiving': {
        'start_date': (11, 22),
        'end_date': (11, 29),
        'activity_tag': string_concat(_('Happy Thanksgiving!'), u' 🦃🥧'),
    },
    'halloween': {
        'start_date': (10, 20),
        'end_date': (10, 31),
        'activity_tag': string_concat(_('Happy Halloween!'), u' 🎃👻'),
    },
    'advent_calendar': {
        'start_date': (12, 01),
        'end_date': (12, 25),
        'ajax_callback': 'adventCalendar',
        'to_context': 'adventCalendar',
        'staff_configurations_settings': ['images', 'badge_image', 'corner_popup_image'],
    },
    'christmas': {
        'start_date': (12, 01),
        'end_date': (12, 31),
        'color': '#d42d2f',
        'secondary_color': '#69ab23',
        'accent_color': '#ffffff',
        'activity_tag': string_concat(_('Merry Christmas!'), u' 🎄🎅'),
    },
}
