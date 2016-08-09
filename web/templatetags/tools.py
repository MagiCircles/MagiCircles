from django import template
register = template.Library()

@register.filter
def mod(value, arg):
    return value % arg == 0

@register.filter
def split(string, splitter=","):
    if string:
        return string.split(splitter)
    return []

@register.filter
def addint(string, int):
    return string + unicode(int)

@register.filter
def times(value):
    return range(value)

@register.filter
def padzeros(value, length):
    if value is None:
        return None
    return ("%0" + str(length) + "d") % value

@register.filter
def isnone(value):
    return value is None

@register.filter
def torfc2822(date):
    return date.strftime("%B %d, %Y %H:%M:%S %z")

@register.filter
def startswith(value, arg):
    return value.startswith(arg)

@register.filter
def get_range(value):
    return range(value)

from django.utils.translation import ugettext_lazy as _
from web.django_translated import t

@register.simple_tag
def t(string):
    return _(string)
