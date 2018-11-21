from django.utils.translation import ugettext_lazy as _

"""
List of terms that we use that django already has, to avoid translating again.
"""

t = {
    '%(field_labels)s can\'t contain only digits.': _('%(field_labels)s can\'t contain only digits.'),
    '%(model_name)s with this %(field_labels)s already exists.': _('%(model_name)s with this %(field_labels)s already exists.'),
    'and': _('and'),
    'Clear': _('Clear'),
    'Download': _('Download'),
    'Email': _('Email'),
    'English': _('English'),
    'Go': _('Go'),
    'Home': _('Home'),
    'Language': _('Language'),
    'No': _('No'),
    'Other': _('Other'),
    'Password': _('Password'),
    'Search': _('Search'),
    'Select a valid choice. %(value)s is not one of the available choices.': _('Select a valid choice. %(value)s is not one of the available choices.'),
    'Thanks for using our site!': _('Thanks for using our site!'),
    'The two password fields didn\'t match.': _('The two password fields didn\'t match.'),
    'This field is required.': _('This field is required.'),
    'URL': _('URL'),
    'User': _('User'),
    'Username': _('Username'),
    'Yes': _('Yes'),
    'Your old password was entered incorrectly. Please enter it again.': _('Your old password was entered incorrectly. Please enter it again.'),
}
