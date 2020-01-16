
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
]

# Can be changed from the Staff Configurations page
# More can be added via "staff_configurations_settings"
STAFF_CONFIGURATIONS_SETTINGS = [
    'site_nav_logo',
    'site_logo',
    'extracss',
    'extrajavascript',
]

DEFAULT_SEASONS = {
    'halloween': {
        'start_date': (10, 20),
        'end_date': (10, 31),
    },
    'advent_calendar': {
        'start_date': (12, 01),
        'end_date': (12, 24),
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
    },
}
