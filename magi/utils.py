# -*- coding: utf-8 -*-
from __future__ import division
import os, string, random, csv, tinify, cStringIO, pytz, simplejson, datetime, io, operator, re
from PIL import Image
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django.conf import settings as django_settings
from django.core.files.temp import NamedTemporaryFile
from django.core.exceptions import ValidationError
from django.core.urlresolvers import resolve
from django.core.validators import BaseValidator, RegexValidator
from django.http import Http404
from django.utils.http import urlquote
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _, get_language
from django.utils.formats import dateformat
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.template import Context
from django.template.loader import get_template
from django.db import models
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist
from django.db.models import Q
from django.forms.models import model_to_dict
from django.forms import NullBooleanField, TextInput, CharField as forms_CharField, CheckboxInput
from django.core.mail import EmailMultiAlternatives
from django.core.files.images import ImageFile
from django_translated import t
from magi.middleware.httpredirect import HttpRedirectException
from magi.default_settings import RAW_CONTEXT

############################################################
# Favorite characters

FAVORITE_CHARACTERS_IMAGES = { id: image for (id, name, image) in getattr(django_settings, 'FAVORITE_CHARACTERS', []) }
FAVORITE_CHARACTERS_NAMES = { id: name for (id, name, image) in getattr(django_settings, 'FAVORITE_CHARACTERS', []) }

############################################################
# Languages

LANGUAGES_DICT = dict(django_settings.LANGUAGES)

############################################################
# Use a dict as a class

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

############################################################
# Permissions and groups utils

def hasGroup(user, group):
    return group in user.preferences.groups

def hasPermission(user, permission):
    """
    Has the given permission.
    """
    if user.is_superuser:
        return True
    for group in user.preferences.groups:
        if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
            return True
    return False

def hasOneOfPermissions(user, permissions):
    """
    Has at least one of the listed permissions.
    """
    if user.is_superuser:
        return True
    for group in user.preferences.groups:
        for permission in permissions:
            if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
                return True
    return False

def hasPermissions(user, permissions):
    """
    Has all the listed permissions.
    """
    if user.is_superuser:
        return True
    permissions = { p: False for p in permissions }
    for group in user.preferences.groups:
        for permission in permissions:
            if permission in user.preferences.GROUPS.get(group, {}).get('permissions', []):
                permissions[permission] = True
    return all(permissions.values())

def groupsForAllPermissions(groups):
    """
    Dictionary of permission -> dict of groups
    """
    a = {}
    for group_name, group in groups.items():
        for permission in group.get('permissions', []):
            if permission not in a:
                a[permission] = {}
            a[permission][group_name] = group
    return a

def allPermissions(groups):
    """
    List of all existing permissions
    """
    return groupsForAllPermissions(groups).keys()

def groupsPerPermission(groups, permission):
    """
    List of groups that have this permission
    """
    return groupsForAllPermissions(groups).get(permission, [])

def groupsWithPermissions(groups, permissions):
    """
    List of groups that all these permissions
    Example:
    - group1: a, b, c
    - group2: a, b, d, e
    groupsWithPermissions(..., [a, b]) -> dict with group1, group2
    groupsWithPermissions(..., [c, a]) -> dict with group1
    """
    g = {}
    for group_name, group in groups.items():
        has_all = True
        for permission in permissions:
            if permission not in group.get('permissions', []):
                has_all = False
                break
        if has_all:
            g[group_name] = group
    return g

def groupsWithOneOfPermissions(groups, permissions):
    """
    List of groups that have one of these permissions
    Example:
    - group1: a, b, c
    - group2: a, b, d, e
    groupsWithOneOfPermissions(..., [c, a]) -> dict with group1, group2
    """
    g = {}
    all = groupsForAllPermissions(groups)
    for permission in permissions:
        for group_name, group in all.get(permission, {}).items():
            g[group_name] = group
    return g

def usersWithGroup(queryset, group):
    """
    Users in this group
    """
    return queryset.filter(preferences__c_groups__contains=u'"{}"'.format(group))

def usersWithGroups(queryset, groups):
    """
    Users in all these groups
    """
    return queryset.filter(**{ 'preferences__c_groups__contains': u'"{}"'.format(group) for group in groups })

def usersWithOneOfGroups(queryset, groups):
    """
    Users in at least one of these groups
    """
    q = Q()
    for group in groups:
        q |= Q(preferences__c_groups__contains=u'"{}"'.format(group))
    return queryset.filter(q)

def usersWithPermission(queryset, groups, permission):
    """
    Users with this permission
    """
    groups = groupsPerPermission(groups, permission)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def usersWithPermissions(queryset, groups, permissions):
    """
    Users with all these permissions
    """
    # TODO: not working, need to find all the combinations of groups that work then make a query with all these groups
    groups = groupsWithPermissions(groups, permissions)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def usersWithOneOfPermissions(queryset, groups, permissions):
    """
    Users with at least one of these permissions
    """
    groups = groupsWithOneOfPermissions(groups, permissions)
    return usersWithOneOfGroups(queryset, groups) if groups else []

def hasPermissionToMessage(from_user, to_user):
    """
    Requires is_followed_by and followed to be added in queryset of to_user
    """
    # Can't send message to self
    if from_user == to_user:
        return False
    # Do not allow if blocked
    if (to_user.id in from_user.preferences.cached_blocked_ids
        or to_user.id in from_user.preferences.cached_blocked_by_ids):
        return False
    # If messages are closed
    if (from_user.preferences.private_message_settings == 'nobody'
        or to_user.preferences.private_message_settings == 'nobody'):
        return False
    # If messages are only open to followed and not followed
    if ((from_user.preferences.private_message_settings == 'follow'
         and not to_user.followed)
        or ((to_user.preferences.private_message_settings == 'follow'
             and not to_user.is_followed_by))):
        return False
    return True

def hasGoodReputation(request):
    """
    Reputation is calculated based on:
    - must be logged in
    - must not have an invalid email address
    - must have joined more than 5 days ago
    - must have at least 1 account added
    """
    if not request.user.is_authenticated():
        return False
    if request.user.preferences.invalid_email:
        return False
    now = timezone.now()
    five_days_ago = now - relativedelta(days=5)
    if request.user.date_joined >= five_days_ago:
        return False
    if len(getAccountIdsFromSession(request)) < 1:
        return False
    return True

def isInboxClosed(request):
    return (not hasGoodReputation(request)
            or request.user.preferences.private_message_settings == 'nobody')

############################################################
# Helpers for MagiCollections

def justReturn(string):
    return lambda *args, **kwargs: string

def propertyFromCollection(property_name):
    def _propertyFromCollection(view):
        return getattr(view.collection, property_name)
    return _propertyFromCollection

"""
Use this to get the standard name for custom templates:
item_template = custom_item_template
"""
custom_item_template = property(lambda view: '{}Item'.format(view.collection.name))

############################################################
# Context for django requests

def globalContext(request):
    context = RAW_CONTEXT.copy()
    context['current'] = resolve(request.path_info).url_name
    context['current_url'] = request.get_full_path() + ('?' if request.get_full_path()[-1] == '/' else '&')
    context['t_site_name'] = context['site_name_per_language'].get(request.LANGUAGE_CODE, context['site_name'])
    context['t_site_image'] = context['site_image_per_language'].get(request.LANGUAGE_CODE, context['site_image'])
    context['t_full_site_image'] = context['full_site_image_per_language'].get(request.LANGUAGE_CODE, context['full_site_image'])
    context['t_email_image'] = context['email_image_per_language'].get(request.LANGUAGE_CODE, context['email_image'])
    context['t_full_email_image'] = context['full_email_image_per_language'].get(request.LANGUAGE_CODE, context['full_email_image'])
    context['hidenavbar'] = 'hidenavbar' in request.GET
    context['request'] = request
    context['javascript_translated_terms_json'] = simplejson.dumps({ term: unicode(_(term)) for term in context['javascript_translated_terms']})
    context['localized_language'] = LANGUAGES_DICT.get(request.LANGUAGE_CODE, '')
    context['current_language'] = get_language()
    context['ajax'] = True
    # Not Ajax
    if '/ajax/' not in context['current_url']:
        context['ajax'] = False
        cuteFormFieldsForContext({
            'language': {
                'selector': '#switchLanguage',
                'choices': django_settings.LANGUAGES,
            },
        }, context)

    # Authenticated
    context['corner_popups'] = OrderedDict()
    if request.user.is_authenticated():
        if isBirthdayToday(request.user.preferences.birthdate):
            context['corner_popups']['happy_birthday'] = {
                'title': mark_safe(u'<span class="fontx1-5">{} 🎉</span>'.format(_('Happy Birthday'))),
                'content': mark_safe(u'<p class="fontx1-5">🗓 {}<br>🎂 {}</p>'.format(
                    request.user.preferences.formatted_birthday_date,
                    request.user.preferences.formatted_age,
                )),
                'image': context['corner_popup_image'],
                'image_overflow': False,
                'allow_close_once': True,
                'allow_close_forever': True,
            }
        if not context['ajax'] and request.user.preferences.invalid_email and context['current'] != 'settings':
            context['corner_popups']['invalid_email'] = {
                'title': _('Your email address is invalid.'),
                'content': _('Some features might not work properly.'),
                'buttons': {
                    'settings': {
                        'title': _('Open {thing}').format(thing=_('Settings').lower()),
                        'url': '/settings/#form',
                    },
                },
                'image': context['corner_popup_image'],
                'image_overflow': False,
                'allow_close_once': True,
                'allow_close_remind': 2,
            }

    # Not authenticated
    else:
        pass

    return context

def getGlobalContext(request):
    if django_settings.GET_GLOBAL_CONTEXT:
        return django_settings.GET_GLOBAL_CONTEXT(request)
    return globalContext(request)

def ajaxContext(request):
    context = RAW_CONTEXT.copy()
    context['request'] = request
    return context

def emailContext():
    context = RAW_CONTEXT.copy()
    context['t_site_name'] = context['site_name_per_language'].get(get_language(), context['site_name'])
    context['t_site_image'] = context['site_image_per_language'].get(get_language(), context['site_image'])
    context['t_full_site_image'] = context['full_site_image_per_language'].get(get_language(), context['full_site_image'])
    context['t_email_image'] = context['email_image_per_language'].get(get_language(), context['email_image'])
    context['t_full_email_image'] = context['full_email_image_per_language'].get(get_language(), context['full_email_image'])
    if context['site_url'].startswith('//'):
        context['site_url'] = 'http:' + context['site_url']
    return context

def getAccountIdsFromSession(request):
    if not request.user.is_authenticated():
        return []
    if 'account_ids' not in request.session:
        request.session['account_ids'] = [
            account.id
            for account in RAW_CONTEXT['account_model'].objects.filter(**{
                    RAW_CONTEXT['account_model'].selector_to_owner():
                    request.user
            })
        ]
    return request.session['account_ids']

class CuteFormType:
    Images, HTML, YesNo, OnlyNone = range(4)
    to_string = ['images', 'html', 'html', 'html']
    default_to_cuteform = ['key', 'value', 'value', 'value']

class CuteFormTransform:
    No, ImagePath, Flaticon, FlaticonWithText = range(4)
    default_field_type = [CuteFormType.Images, CuteFormType.Images, CuteFormType.HTML, CuteFormType.HTML]

def cuteFormFieldsForContext(cuteform_fields, context, form=None, prefix=None, ajax=False):
    """
    Adds the necesary context to call cuteform in javascript.
    Prefix is a prefix to add to all selectors. Can be useful to isolate your cuteform within areas of your page.
    cuteform_fields: must be a dictionary of {
      field_name: {
        type: CuteFormType.Images, .HTML, .YesNo or .OnlyNone, will be images if not specified,
        to_cuteform: 'key' or 'value' or lambda that takes key and value, will be 'key' if not specified,
        choices: list of pair, if not specified will use form
        selector: will be #id_{field_name} if not specified,
        transform: when to_cuteform is a lambda: CuteFormTransform.No, .ImagePath, .Flaticon, .FlaticonWithText
        image_folder: only when to_cuteform = 'images' or transform = 'images', will specify the images path,
        extra_settings: dictionary of options passed to cuteform,
    }
    """
    if not cuteform_fields:
        return
    if 'cuteform_fields' not in context:
        context['cuteform_fields'] = {}
        context['cuteform_fields_json'] = {}

    empty = context['full_empty_image']
    empty_image = u'<img src="{}" class="empty-image">'.format(empty)

    for field_name, field in cuteform_fields.items():
        transform = field.get('transform', CuteFormTransform.No)
        field_type = field.get('type', CuteFormTransform.default_field_type[transform])
        if 'selector' not in field:
            field['selector'] = '#id_{}'.format(field_name)
        if 'to_cuteform' not in field:
            field['to_cuteform'] = CuteFormType.default_to_cuteform[field_type]

        # Get choices
        choices = field.get('choices', [])
        if not choices and form and field_name in form.fields:
            if hasattr(form.fields[field_name], 'queryset'):
                choices = BLANK_CHOICE_DASH + list(form.fields[field_name].queryset)
            elif hasattr(form.fields[field_name], 'choices'):
                choices = form.fields[field_name].choices
        if choices and field_type in [CuteFormType.YesNo, CuteFormType.OnlyNone]:
            transform = CuteFormTransform.FlaticonWithText
        if not choices and field_type in [CuteFormType.YesNo, CuteFormType.OnlyNone]:
            true = u'<i class="flaticon-checked"></i> {}'.format(
                _('Yes') if field_type == CuteFormType.YesNo else _('Only'),
            )
            false = u'<i class="flaticon-delete"></i> {}'.format(
                _('No') if field_type == CuteFormType.YesNo else _('None'),
            )
            if not form or field_name not in form or isinstance(form.fields[field_name], NullBooleanField):
                choices = [
                    ('1', empty_image),
                    ('2', true),
                    ('3', false),
                ]
            else:
                choices = [
                    ('0', true),
                    ('1', false),
                ]
        if not choices:
            continue
        selector = u'{}{}'.format((prefix if prefix else ''), field['selector'])
        # Initialize cuteform dict for field
        context['cuteform_fields'][selector] = {
            CuteFormType.to_string[field_type]: {},
        }
        # Add title if any
        if 'title' in field:
            context['cuteform_fields'][selector]['title'] = _(u'Select {}').format(unicode(field['title']).lower())
        # Add extra settings if any
        if 'extra_settings' in field:
            context['cuteform_fields'][selector].update(field['extra_settings'] if not ajax else {
                k:v for k, v in field['extra_settings'].items()
                if 'modal' not in k })
        for choice in choices:
            key, value = choice if isinstance(choice, tuple) else (choice.id, choice)
            if key == '':
                cuteform = empty if field_type == CuteFormType.Images else empty_image
            else:
                # Get the cuteform value with to_cuteform
                if field['to_cuteform'] == 'key':
                    cuteform_value = key
                elif field['to_cuteform'] == 'value':
                    cuteform_value = value
                else:
                    cuteform_value = field['to_cuteform'](key, value)
                # Transform to image path
                if (field_type == CuteFormType.Images
                    and (field['to_cuteform'] in ['key', 'value']
                         or transform == CuteFormTransform.ImagePath)):
                    cuteform = staticImageURL(
                        unicode(cuteform_value),
                        folder=field.get('image_folder', field_name),
                        extension='png',
                    )
                # Transform to flaticon
                elif transform in [CuteFormTransform.Flaticon, CuteFormTransform.FlaticonWithText]:
                    cuteform = u'<i class="flaticon-{icon}"></i>{text}'.format(
                        icon=cuteform_value,
                        text=u' {}'.format(value) if transform == CuteFormTransform.FlaticonWithText else '',
                    )
                    if transform == CuteFormTransform.Flaticon:
                        cuteform = u'<div data-toggle="tooltip" data-placement="top" data-trigger="hover" data-html="true" title="{}">{}</div>'.format(value, cuteform)
                else:
                    cuteform = unicode(cuteform_value)
            # Add in key, value in context for field
            context['cuteform_fields'][selector][CuteFormType.to_string[field_type]][key] = cuteform

        # Store a JSON version to be displayed in Javascript
        context['cuteform_fields_json'][selector] = simplejson.dumps(context['cuteform_fields'][selector])

############################################################
# Database upload to

class _uploadToBase(object):
    def __init__(self, prefix, length=6, limit=100):
        self.prefix = prefix
        self.length = length
        self.limit = limit

    def __call__(self, instance, filename):
        name, extension = os.path.splitext(filename)
        if not extension:
            extension = '.png'
        prefix = u''.join([
            RAW_CONTEXT['static_uploaded_files_prefix'],
            self.prefix,
        ]) + u'/'
        suffix = extension
        name = self.get_name(
            instance, filename,
            getattr(self, 'limit', 100) - len(prefix) - len(suffix) - 1,
        )
        return u'{}{}{}'.format(prefix, name, suffix)

@deconstructible
class uploadToKeepName(_uploadToBase):
    def get_name(self, instance, filename, limit_to):
        return u'{}{}'.format(
            filename[:(limit_to - self.length)],
            randomString(self.length),
        )

@deconstructible
class uploadToRandom(_uploadToBase):
    def __init__(self, prefix, length=30, *args, **kwargs):
        super(uploadToRandom, self).__init__(prefix, length=length, *args, **kwargs)

    def get_name(self, instance, filename, limit_to):
        return randomString(self.length)[:limit_to]

@deconstructible
class uploadItem(_uploadToBase):
    def get_name(self, instance, filename, limit_to):
        id = unicode(instance.id if instance.id else randomString(6))
        return u'{id}{string}-{random}'.format(
            id=id,
            string=tourldash(unicode(instance))[:(limit_to - len(id) - self.length)],
            random=randomString(self.length),
        )

@deconstructible
class uploadThumb(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadThumb, self).__init__(
            prefix + ('thumb' if prefix.endswith('/') else '/thumb'),
            *args, **kwargs
        )

@deconstructible
class uploadTthumb(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadTthumb, self).__init__(
            prefix + ('tthumb' if prefix.endswith('/') else '/tthumb'),
            *args, **kwargs
        )

@deconstructible
class uploadTiny(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(uploadTiny, self).__init__(
            prefix + ('tiny' if prefix.endswith('/') else '/tiny'),
            *args, **kwargs
        )

@deconstructible
class upload2x(uploadItem):
    def __init__(self, prefix, *args, **kwargs):
        super(upload2x, self).__init__(
            prefix + ('2x' if prefix.endswith('/') else '/2x'),
            *args, **kwargs
        )

############################################################
# Get MagiCollection(s)

def getMagiCollections():
    try:
        return RAW_CONTEXT['magicollections']
    except KeyError:
        return []

def getMagiCollection(collection_name):
    """
    May return None if called before the magicollections have been initialized
    """
    if 'magicollections' in RAW_CONTEXT and collection_name in RAW_CONTEXT['magicollections']:
        return RAW_CONTEXT['magicollections'][collection_name]
    return None

############################################################
# Date to RFC 2822 format

def torfc2822(date):
    return date.strftime("%B %d, %Y %H:%M:%S %z")

############################################################
# Birthday within

def birthdays_within(days_after, days_before=0, field_name='birthday'):
    now = timezone.now()
    after = now - datetime.timedelta(days=days_before)
    before = now + datetime.timedelta(days=days_after)

    monthdays = [(now.month, now.day)]
    while after <= before:
        monthdays.append((after.month, after.day))
        after += datetime.timedelta(days=1)

    # Tranform each into queryset keyword args.
    monthdays = (dict(zip((
        u'{}__month'.format(field_name),
        u'{}__day'.format(field_name),
    ), t)) for t in monthdays)

    # Compose the djano.db.models.Q objects together for a single query.
    return reduce(operator.or_, (Q(**d) for d in monthdays))

def isBirthdayToday(date):
    if not date:
        return False
    today = datetime.date.today()
    return (
        today.day == date.day
        and today.month == date.month
    )

def getNextBirthday(date):
    today = datetime.date.today()
    birthday = date

    is_feb29 = False
    if birthday.month == 2 and birthday.day == 29:
        is_feb29 = True
        birthday = birthday.replace(
            month=date.month + 1,
            day=1,
        )

    birthday = birthday.replace(year=today.year)
    if birthday < today:
        birthday = birthday.replace(year=today.year + 1)

    if is_feb29:
        try: birthday = birthday.replace(month=2, day=29)
        except ValueError: pass
    return birthday

def birthdayURL(user):
    if not user.preferences.birthdate:
        return None
    return 'https://www.timeanddate.com/countdown/birthday?iso={date}T00&msg={username}%27s+birthday'.format(
        date=dateformat.format(getNextBirthday(user.preferences.birthdate), "Ymd"),
        username=user.username,
    )

############################################################
# Event status using start and end date

def getEventStatus(start_date, end_date):
    if not end_date or not start_date:
        return None
    now = timezone.now()
    if now > end_date:
        return 'ended'
    elif now > start_date:
        return 'current'
    return 'future'

def filterEventsByStatus(queryset, status, prefix=''):
    if status == 'all':
        return queryset
    now = timezone.now()
    if status == 'ended':
        return queryset.filter(**{
            u'{}end_date__lt'.format(prefix): now,
        })
    elif status == 'current':
        return queryset.filter(**{
            u'{}start_date__lte'.format(prefix): now,
            u'{}end_date__gte'.format(prefix): now,
        })
    elif status == 'future':
        return queryset.filter(**{
            u'{}start_date__gt'.format(prefix): now,
        })
    return queryset

############################################################
# Send email

def send_email(subject, template_name, to=[], context=None, from_email=django_settings.AWS_SES_RETURN_PATH):
    if 'template_name' != 'notification':
        to.append(django_settings.LOG_EMAIL)
    subject = subject.replace('\n', '').replace('\r', '')
    if not context:
        context = emailContext()
    context = Context(context)
    plaintext = get_template('emails/' + template_name + '.txt').render(context)
    htmly = get_template('emails/' + template_name + '.html').render(context)
    email = EmailMultiAlternatives(subject, plaintext, from_email, to)
    email.attach_alternative(htmly, "text/html")
    email.send()

############################################################
# Various string/int/list tools

def randomString(length, choice=(string.ascii_letters + string.digits)):
    return ''.join(random.SystemRandom().choice(choice) for _ in range(length))

def ordinalNumber(n):
    return "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])

def tourldash(string):
    if not string:
        return ''
    s =  u''.join(e if e.isalnum() else u'-' for e in string)
    return u'-'.join([s for s in s.split(u'-') if s])

def toHumanReadable(string):
    return string.lower().replace('_', ' ').replace('-', ' ').capitalize()

def jsv(v):
    if isinstance(v, list) or isinstance(v, dict):
        return mark_safe(simplejson.dumps(v))
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, str) or isinstance(v, unicode):
        return mark_safe(u'"{}"'.format(v))
    return v

def templateVariables(string):
    return [x[1] for x in string._formatter_parser() if x[1]]

def snakeToCamelCase(string):
    return ''.join(x.capitalize() or '_' for x in string.split('_'))

def listUnique(list):
    return OrderedDict([(item, None) for item in list]).keys()

############################################################
# Redirections

def redirectToProfile(request, account=None):
    raise HttpRedirectException(u'/user/{}/{}/'.format(request.user.id, request.user.username, '#{}'.format(account.id) if account else ''))

def redirectWhenNotAuthenticated(request, context, next_title=None):
    if not request.user.is_authenticated():
        if context.get('current_url', '').startswith('/ajax/'):
            raise HttpRedirectException(u'/signup/')
        raise HttpRedirectException(u'/signup/{}'.format((u'?next={}{}'.format(context['current_url'], u'&next_title={}'.format(unicode(next_title)) if next_title else u'')) if 'current_url' in context else ''))

############################################################
# Fail safe get_object_or_404

def get_one_object_or_404(queryset, *args, **kwargs):
    """
    Equivalent of get_object_or_404 but if more than 1, will return first result
    """
    existing = queryset.filter(**kwargs)
    try:
        return existing[0]
    except IndexError:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)

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

def modelHasField(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

class ColorInput(TextInput):
    input_type = 'color'

    def render(self, name, value, attrs=None):
        rendered = super(ColorInput, self).render(name, value, attrs=attrs)
        if not self.is_required:
            return mark_safe(u'{input} <input type="checkbox" name="unset-{name}"{checked}> {none}'.format(
                input=rendered,
                name=name,
                none=t['Clear'],
                checked='' if value else ' checked',
            ))
        return rendered

    def value_from_datadict(self, data, files, name):
        value = super(ColorInput, self).value_from_datadict(data, files, name)
        if not self.is_required and CheckboxInput().value_from_datadict(
                data, files, u'unset-{}'.format(name)):
            return None
        return value

class ColorFormField(forms_CharField):
    pass

class ColorField(models.CharField):
    default_validators = [
        RegexValidator(
            re.compile('^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'),
            u'Enter a valid hex color.',
            'invalid',
        ),
    ]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['form_class'] = ColorFormField
        kwargs['widget'] = ColorInput
        return super(ColorField, self).formfield(**kwargs)

############################################################
# Set a field in a sub dictionary

def setSubField(fields, field_name, value, key='icon'):
    if isinstance(fields, list):
        for name, details in fields:
            if name == field_name:
                details[key] = value(field_name) if callable(value) else value
    else:
        if field_name in fields:
            fields[field_name][key] = value(field_name) if callable(value) else value

def getSubField(fields, l, default=None):
    ret = fields
    for i in l:
        if isinstance(ret, dict):
            try:
                ret = ret[i]
            except KeyError:
                return default
        else:
            try:
                ret = getattr(ret, i)
            except AttributeError:
                return default
    return ret

############################################################
# Join / Split data stored as string in database

def split_data(data):
    """
    Takes a unicode CSV string and return a list of strings.
    """
    if not data:
        return []
    if isinstance(data, list):
        return data
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def unicode_csv_reader(unicode_csv_data, **kwargs):
        csv_reader = csv.reader(utf_8_encoder(unicode_csv_data), **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    reader = unicode_csv_reader([data])
    for reader in reader:
        return [r for r in reader]
    return []

def join_data(*args):
    """
    Takes a list of unicode strings and return a CSV string.
    """
    data = u'\"' + u'","'.join([unicode(value).replace('\n', ' ').replace('\r', ' ').replace('"','\"') for value in args]) + u'\"'
    return data if data != '""' else None

############################################################
# Validators

def FutureOnlyValidator(value):
    if value < datetime.date.today():
        raise ValidationError(_('This date has to be in the future.'), code='future_value')

def PastOnlyValidator(value):
    if value > datetime.date.today():
        raise ValidationError(_('This date cannot be in the future.'), code='past_value')

############################################################
# Image manipulation

def dataToImageFile(data):
    image = NamedTemporaryFile(delete=False)
    image.write(data)
    image.flush()
    return ImageFile(image)

def imageThumbnailFromData(data, filename, width=200, height=200):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    image = Image.open(cStringIO.StringIO(data))
    image.thumbnail((width, height))
    output = io.BytesIO()
    image.save(output, format={
        'png': 'PNG',
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'gif': 'GIF',
    }.get(extension.lower(), 'PNG'))
    return dataToImageFile(output.getvalue())

def shrinkImageFromData(data, filename, settings={}):
    """
    Optimize images with TinyPNG
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    api_key = getattr(django_settings, 'TINYPNG_API_KEY', None)
    if not api_key or extension not in ['.png', '.jpg', '.jpeg']:
        return dataToImageFile(data)
    tinify.key = api_key
    source = tinify.from_buffer(data)
    if settings.get('resize', None) == 'fit':
        image = Image.open(cStringIO.StringIO(data))
        max_width = settings.get('max_width', django_settings.MAX_WIDTH)
        max_height = settings.get('max_height', django_settings.MAX_HEIGHT)
        min_width = settings.get('min_width', django_settings.MIN_WIDTH)
        min_height = settings.get('min_height', django_settings.MIN_HEIGHT)
        width, height = image.size
        if width > max_width:
            height = (max_width / width) * height
            width = max_width
        if height > max_height:
            width = (max_height / height) * width
            height = max_height
        if height < min_height:
            height = min_height
        if width < min_width:
            width = min_width
        source = source.resize(
            method='fit',
            width=int(width),
            height=int(height),
        )
    elif settings.get('resize', None) == 'cover':
        source = source.resize(
            method='cover',
            width=settings.get('width', 300),
            height=settings.get('height', 300),
        )
    elif settings.get('resize', None) == 'scale':
        if settings.get('width', None):
            source = source.resize(
                method='scale',
                width=settings['width'],
            )
        if settings.get('height', None):
            source = source.resize(
                method='scale',
                height=settings['height'],
            )
    elif settings.get('resize', None) == 'thumb':
        source = source.resize(
            method='thumb',
            width=settings.get('width', 300),
            height=settings.get('height', 300),
        )
    try:
        data = source.to_buffer()
    except: # Retry without resizing
        try:
            data = tinify.from_buffer(data).to_buffer()
        except: # Just return the original data
            pass
    return dataToImageFile(data)

############################################################
# Image URLs

def staticImageURL(path, folder=None, extension=None, versionned=True, full=False):
    if not path and not folder and not extension:
        return None
    path = unicode(path)
    if path.startswith('//') or path.startswith('http://') or path.startswith('https://'):
        return path
    return u'{static}img/{folder}{path}{extension}{version}'.format(
        static=RAW_CONTEXT['static_url'] if not full else RAW_CONTEXT['full_static_url'],
        folder=u'{}/'.format(folder) if folder else '',
        path=path,
        extension=u'.{}'.format(extension) if extension else '',
        version=u'' if not versionned else u'{suffix}{version}'.format(
            suffix='?' if '?' not in path and '?' not in (extension or '') else '&',
            version=RAW_CONTEXT['static_files_version'],
        ),
    )

def linkToImageURL(link):
    return staticImageURL(u'links/{}'.format(link.i_type), extension=u'png')

############################################################
# HTML tools

def toTimeZoneDateTime(date, timezones, ago=False):
    if not date:
        return u''
    date = torfc2822(date)
    return u'{}{}'.format(u'<br>'.join([
        u'<span class="timezone" data-to-timezone="{timezone}"><span class="datetime">{date}</span>(<span class="current_timezone">UTC</span>)</span>'.format(
            timezone=timezone,
            date=date,
        )
        for timezone in timezones
    ]), u'<br><small class="text-muted"><span class="timezone" data-timeago="true" style="display: none;"><span class="datetime">{date}</span></span></small>'.format(
        date=date,
    ) if ago else '')

def toCountDown(date, sentence, classes=None):
    if not date or date < timezone.now():
        return u''
    return u'<span class="countdown {classes}" data-date="{date}" data-format="{sentence}"></h4>'.format(
        date=torfc2822(date), sentence=sentence, classes=u' '.join(classes or []),
    )

def markdownHelpText(request=None):
    if ('help' in RAW_CONTEXT['all_enabled']
        and (not request or request.LANGUAGE_CODE not in RAW_CONTEXT['languages_cant_speak_english'])):
        return mark_safe(u'{} <a href="/help/Markdown" target="_blank">{}.</a>'.format(
            _(u'You may use Markdown formatting.'),
            _(u'Learn more'),
        ))
    else:
        return _(u'You may use Markdown formatting.')

############################################################
# Async update function

def locationOnChange(user_preferences):
    # This function is only called by the async script so to avoid loading Nominatim when the site is running,
    # it's included within the function
    import sys
    from geopy.geocoders import Nominatim
    geolocator = Nominatim()
    try:
        location = geolocator.geocode(user_preferences.location)
        if location is not None:
            user_preferences.latitude = location.latitude
            user_preferences.longitude = location.longitude
            user_preferences.location_changed = False
            user_preferences.save()
            print user_preferences.user, user_preferences.location, user_preferences.latitude, user_preferences.longitude
        else:
            user_preferences.location_changed = False
            user_preferences.save()
            print user_preferences.user, user_preferences.location, 'Invalid location'
    except:
        print u'{} {} Error, {}'.format(user_preferences.user, user_preferences.location, sys.exc_info()[0])
        # Will not mark as not changed, so it will be retried at next iteration
    return True

############################################################
# Translations

def duplicate_translation(model, field, term, only_for_language=None, print_log=True, html_log=False):
    logs = []
    items = list(model.objects.filter(**{ field: term }))
    known_translations = []
    for item in items:
        for language, translation in getattr(item, u'{}s'.format(field[2:] if field.startswith('m_') else field)).items():
            if only_for_language and language != only_for_language:
                continue
            if language not in known_translations:
                for s_item in items:
                    existing = getattr(s_item, u'{}s'.format(field[2:] if field.startswith('m_') else field))
                    if language not in existing:
                        s_item.add_d(u'{}s'.format(field), language, translation[1] if field.startswith('m_') else translation)
                        log = u'Add {language} translations to {open_a}#{id} {item}{close_a}'.format(
                            language=language,
                            open_a=u'<a href="{}" target="_blank">'.format(s_item.http_item_url) if html_log else '',
                            id=s_item.id,
                            item=s_item,
                            close_a='</a>' if html_log else '',
                        )
                        if print_log:
                            print log
                        logs.append(log)
                    s_item.save()
                known_translations.append(language)
    return logs

def translations_count_has(model, field, term, language):
    return model.objects.filter(**{
        field: term,
        u'd_{}s__icontains'.format(field): '"{}"'.format(language),
    }).count()

def translations_count_to_apply_to(model, field, term, language):
    return model.objects.filter(**{
        field: term,
    }).exclude(**{
        u'd_{}s__icontains'.format(field): '"{}"'.format(language),
    }).count()

def find_all_translations(model, field, only_for_language=None, with_count_has=True, with_count_to_apply_to=True):
    """
    Returns a dict of:
    base term in English
    -> (Dict of:
       Language
       -> (List of translations,
           Count other item with term present in that language,
           Count how many items could get their translation duplicated automatically),
       total can be duplicated to,
       display term (for markdown))
    """
    translations = {}
    for item in model.objects.filter(**{ u'{}__isnull'.format(field): False}).exclude(**{ field: '' }):
        term = getattr(item, field)
        if term not in translations:
            translations[term] = {}
        for language, translation in getattr(item, u'{}s'.format(field[2:] if field.startswith('m_') else field)).items():
            if only_for_language and language != only_for_language:
                continue
            if language not in translations[term]:
                translations[term][language] = (
                    [],
                    translations_count_has(model, field, term, language) if with_count_has else 0,
                    translations_count_to_apply_to(model, field, term, language) if with_count_to_apply_to else 0,
                )
            if translation not in translations[term][language][0]:
                translations[term][language][0].append(
                    mark_safe(u'<p class="to-markdown">{}</p>'.format(translation[1]))
                    if field.startswith('m_') else translation)
    for term in translations.keys():
        translations[term] = (
            translations[term],
            reduce(lambda a, b: a + b, [_t[2] for _t in translations[term].values()], 0),
            mark_safe(u'<p class="to-markdown">{}</p>'.format(term)) if field.startswith('m_') else term,
        )

    return translations

def translationURL(value, from_language='en', to_language=None, with_wrapper=True):
    url = 'https://translate.google.com/#{from_language}/{to_language}/{value}'.format(
        to_language=to_language if to_language else get_language(),
        from_language=from_language,
        value=urlquote(value),
    )
    if with_wrapper:
        return u'<a href="{url}" target="_blank"> {value} <i class="flaticon-link"></i></a>'.format(
            url=url,
            value=value,
        )
    return url
