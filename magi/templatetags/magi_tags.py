from django.utils.translation import ugettext_lazy as _
from django import template
from magi import models
from magi.settings import RAW_CONTEXT
from magi.utils import AttrDict, torfc2822, translationURL as _translationURL

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
def getFormAsList(forms, form):
    if forms:
        return forms
    if form:
        return {'form': form}
    return {}

@register.simple_tag(takes_context=True)
def navbarGetURL(context, link):
    if link.get('get_url', None):
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

@register.simple_tag()
def translationURL(*args, **kwargs):
    if 'with_wrapper' not in kwargs:
        kwargs['with_wrapper'] = False
    return _translationURL(*args, **kwargs)
