import time
from django.utils.translation import ugettext_lazy as _, string_concat
from django import template
from django.conf import settings
from web import models
from web.settings import SITE_STATIC_URL, FAVORITE_CHARACTER_TO_URL, RAW_CONTEXT, ENABLED_COLLECTIONS
from web.utils import AttrDict

register = template.Library()

@register.filter
def avatar(user, size=200):
    return models.avatar(user, size)

@register.tag
def forceLoadRawContext(parser, token):
    return EventNode()

class EventNode(template.Node):
    def render(self, context):
        if 'site_url' not in context:
            context.update(RAW_CONTEXT)
            context['request'] = AttrDict({
                'user': context['user'],
            })
        return ''

@register.filter
def linkUrl(link):
    if link.type in models.LINK_URLS:
        if hasattr(link.value, 'id'):
            return models.LINK_URLS[link.type].format(link.value.id)
        if link.type == 'Location' and 'map' in RAW_CONTEXT['all_enabled'] and link.latlong:
            return '/map/?center={}&zoom=10'.format(link.latlong)
        return models.LINK_URLS[link.type].format(link.value)
    if link.raw_value:
        return FAVORITE_CHARACTER_TO_URL(link)
    return '#'

@register.simple_tag(takes_context=True)
def linkImageURL(context, link):
    if link.type in models.LINK_URLS:
        return '{}img/links/{}.png'.format(context['static_url'], link.type)
    return link.image

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
    return ENABLED_COLLECTIONS[name]['plural_name']
