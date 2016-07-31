from django.utils.translation import ugettext_lazy as _

"""
List of terms that we use that django already has, to avoid translating again.
"""

t = {
    "Home": _("Home"),
    "%(model_name)s with this %(field_labels)s already exists.": _("%(model_name)s with this %(field_labels)s already exists."),
    "User": _("User"),
    "Email": _("Email"),
    "%(field_labels)s can't contain only digits.": _("%(field_labels)s can't contain only digits."),
    "Username": _("Username"),
    "Your old password was entered incorrectly. Please enter it again.": _("Your old password was entered incorrectly. Please enter it again."),
    "The two password fields didn't match.": _("The two password fields didn't match."),
    "Go": _("Go"),
    "Search": _("Search"),
    "Thanks for using our site!": _("Thanks for using our site!"),
    "and": _("and"),
    "Password": _("Password"),
    "User": _("User"),
}
