import time
from django.utils.translation import ugettext_lazy as _, string_concat
from django import template
from django.conf import settings
from magi import models
from magi.settings import SITE_STATIC_URL, FAVORITE_CHARACTER_TO_URL, RAW_CONTEXT
from magi.utils import AttrDict, getMagiCollection, torfc2822

register = template.Library()

register.filter('torfc2822', torfc2822)

@register.filter
def avatar(user, size=200):
    return models.avatar(user, size)

@register.tag
def forceLoadRawContext(parser, token):
    return EventNode()

class EventNode(template.Node):
    def render(self, context):
        if 'site_url' not in context:
            for key, value in RAW_CONTEXT.items():
                if key not in context:
                    context[key] = value
            context['request'] = AttrDict({
                'user': context['user'],
            })
        return ''

@register.filter
def linkShowAuth(link, user):
    if user.is_authenticated():
        if link['auth'][0] and link['staff_required']:
            return user.is_staff
        return link['auth'][0]
    return link['auth'][1] and not link['staff_required']

@register.filter
def getFormAsList(forms, form):
    if forms:
        return forms
    if form:
        return {'form': form}
    return {}

@register.simple_tag(takes_context=True)
def navbarGetURL(context, link):
    if link['get_url']:
        return link['get_url'](context)
    return link['url']

@register.simple_tag(takes_context=True)
def navbarTitle(context, link):
    title = link['title']
    if callable(title):
        return title(context)
    if title:
        return _(title)
    return title

@register.filter
def translated(value):
    return _(value)

@register.filter
def collectionGetPlural(name):
    return getMagiCollection(name).plural_name
