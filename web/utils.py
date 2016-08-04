import string, random
from django.conf import settings
from django.core.urlresolvers import resolve
from django.utils import translation
from django.template import Context
from django.template.loader import get_template
from django.db import models
from django.forms.models import model_to_dict
from django.core.mail import EmailMultiAlternatives
from web.middleware.httpredirect import HttpRedirectException
from default_settings import RAW_CONTEXT

############################################################
# Use a dict as a class

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

############################################################
# Context for django requests

def globalContext(request):
    context = RAW_CONTEXT.copy()
    context['current'] = resolve(request.path_info).url_name
    context['current_url'] = request.get_full_path() + ('?' if request.get_full_path()[-1] == '/' else '&')
    context['hidenavbar'] = 'hidenavbar' in request.GET
    context['request'] = request
    if request.user.is_authenticated() and not request.user.is_anonymous():
        translation.activate(request.user.preferences.language)
        request.LANGUAGE_CODE = translation.get_language()
    return context

def getGlobalContext(request):
    from web.settings import GET_GLOBAL_CONTEXT
    if GET_GLOBAL_CONTEXT:
        return GET_GLOBAL_CONTEXT(request)
    return globalContext(request)

def ajaxContext(request):
    context = RAW_CONTEXT.copy()
    return context

def emailContext():
    context = RAW_CONTEXT.copy()
    if context['site_url'].startswith('//'):
        context['site_url'] = 'http:' + context['site_url']
    if context['site_image'].startswith('//'):
        context['site_image'] = 'http:' + context['site_image']
    return context

############################################################
# Send email

def send_email(subject, template_name, to=[], context={}, from_email=settings.AWS_SES_RETURN_PATH):
    if 'template_name' != 'notification':
        to.append(settings.LOG_EMAIL)
    context = Context(context)
    plaintext = get_template('emails/' + template_name + '.txt').render(context)
    htmly = get_template('emails/' + template_name + '.html').render(context)
    email = EmailMultiAlternatives(subject, plaintext, from_email, to)
    email.attach_alternative(htmly, "text/html")
    email.send()

############################################################
# Various string/int tools

def randomString(length, choice=(string.ascii_letters + string.digits)):
    return ''.join(random.SystemRandom().choice(choice) for _ in range(length))

def ordinalNumber(n):
    return "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

def tourldash(string):
    s =  u''.join(e if e.isalnum() else u'-' for e in string)
    return u'-'.join([s for s in s.split(u'-') if s])

############################################################
# Redirections

def redirectToProfile(request, account=None):
    raise HttpRedirectException(u'/user/{}/{}/'.format(request.user.id, request.user.username, '#{}'.format(account.id) if account else ''))

def redirectWhenNotAuthenticated(request, context):
    if not request.user.is_authenticated():
        raise HttpRedirectException(u'/signup/?next={}'.format(context['current_url']))

############################################################
# Dump model

def dumpModel(instance):
    """
    Take an instance of a model and transform it into a string with all its info.
    Allows to delete an instance without losing data.
    """
    dump = model_to_dict(instance)
    for key in dump.keys():
        if isinstance(dump[key], models.Model):
            dump[key] = dump[key].id
        else:
            dump[key] = unicode(dump[key])
    return dump
