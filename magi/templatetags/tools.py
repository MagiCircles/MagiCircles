import re
from django import template
from django.utils.translation import ugettext_lazy as _
from magi.django_translated import t

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
def startswith(value, arg):
    return value.startswith(arg)

@register.simple_tag
def t(string):
    return _(string)

@register.simple_tag
def format(string, **kwargs):
    return string.format(**kwargs)

@register.simple_tag
def trans_format(string, **kwargs):
    return _(string).format(**kwargs)

@register.simple_tag
def anon_format(string, **kwargs):
    return string.format(*kwargs.values())

@register.simple_tag
def trans_anon_format(string, **kwargs):
    return _(string).format(*kwargs.values())

@register.filter
def orcallable(var_or_callable):
    if callable(var_or_callable):
        return _(var_or_callable())
    return _(var_or_callable)

@register.filter
def isList(thing):
    return isinstance(thing, list)

@register.filter
def modelName(thing):
    return thing.__class__.__name__

@register.filter
def call(function, parameter):
    return function(parameter)

@register.simple_tag(takes_context=True)
def callWithContext(context, dict, function, p1=None, p2=None, p3=None):
    if function in dict:
        context['result_of_callwithcontext'] = dict[function](context, *[p for p in [p1, p2, p3] if p is not None])
    return ''

@register.filter
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        if callable(getattr(value, arg)):
            return getattr(value, arg)()
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    elif re.compile("^\d+$").match(str(arg)) and len(value) > int(arg):
        return value[int(arg)]
    elif str(arg) in value:
        return value.get(arg)
    try: return value[arg]
    except: return settings.TEMPLATE_STRING_IF_INVALID
