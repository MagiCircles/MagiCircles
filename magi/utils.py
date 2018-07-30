from __future__ import division
import os, string, random, csv, tinify, cStringIO, pytz, simplejson, datetime, io, operator
from PIL import Image
from collections import OrderedDict
from django.conf import settings as django_settings
from django.core.files.temp import NamedTemporaryFile
from django.core.exceptions import ValidationError
from django.core.urlresolvers import resolve
from django.core.validators import BaseValidator
from django.http import Http404
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
from django.forms import NullBooleanField
from django.core.mail import EmailMultiAlternatives
from django.core.files.images import ImageFile
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
    context['hidenavbar'] = 'hidenavbar' in request.GET
    context['request'] = request
    context['javascript_translated_terms_json'] = simplejson.dumps({ term: unicode(_(term)) for term in context['javascript_translated_terms']})
    context['localized_language'] = LANGUAGES_DICT.get(get_language(), '')
    context['current_language'] = get_language()
    if '/ajax/' not in context['current_url']:
        context['ajax'] = False
        cuteFormFieldsForContext({
            'language': {
                'selector': '#switchLanguage',
                'choices': django_settings.LANGUAGES,
            },
        }, context)
    else:
        context['ajax'] = True
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

@deconstructible
class uploadToKeepName(object):
    def __init__(self, prefix, length=6):
        self.prefix = prefix
        self.length = length

    def __call__(self, instance, filename):
        name, extension = os.path.splitext(filename)
        name = (
            RAW_CONTEXT['static_uploaded_files_prefix']
            + self.prefix
            + name
            + randomString(self.length)
            + extension
        )
        return name

@deconstructible
class uploadToRandom(object):
    def __init__(self, prefix, length=30):
        self.prefix = prefix
        self.length = length

    def __call__(self, instance, filename):
        name, extension = os.path.splitext(filename)
        return RAW_CONTEXT['static_uploaded_files_prefix'] + self.prefix + randomString(self.length) + extension

@deconstructible
class uploadItem(object):
    def __init__(self, prefix, length=6):
        self.prefix = prefix
        self.length = length

    def __call__(self, instance, filename):
        _, extension = os.path.splitext(filename)
        if not extension:
            extension = '.png'
        return u'{static_uploaded_files_prefix}{prefix}/{id}{string}-{random}{extension}'.format(
            static_uploaded_files_prefix=RAW_CONTEXT['static_uploaded_files_prefix'],
            prefix=self.prefix,
            id=instance.id if instance.id else randomString(6),
            string=tourldash(unicode(instance)),
            random=randomString(self.length),
            extension=extension,
        )

@deconstructible
class uploadThumb(uploadItem):
    def __init__(self, prefix, length=6):
        self.prefix = prefix + ('thumb' if prefix.endswith('/') else '/thumb')
        self.length = length

@deconstructible
class uploadTthumb(uploadItem):
    def __init__(self, prefix, length=6):
        self.prefix = prefix + ('tthumb' if prefix.endswith('/') else '/tthumb')
        self.length = length

@deconstructible
class uploadTiny(uploadItem):
    def __init__(self, prefix, length=6):
        self.prefix = prefix + ('tiny' if prefix.endswith('/') else '/tiny')
        self.length = length

@deconstructible
class upload2x(uploadItem):
    def __init__(self, prefix, length=6):
        self.prefix = prefix + ('2x' if prefix.endswith('/') else '/2x')
        self.length = length

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

def send_email(subject, template_name, to=[], context={}, from_email=django_settings.AWS_SES_RETURN_PATH):
    if 'template_name' != 'notification':
        to.append(django_settings.LOG_EMAIL)
    subject = subject.replace('\n', '')
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
    data = u'\"' + u'","'.join([unicode(value).replace('"','\"') for value in args]) + u'\"'
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

def staticImageURL(path, folder=None, extension=None, versionned=True):
    if not path and not folder and not extension:
        return None
    path = unicode(path)
    if path.startswith('//') or path.startswith('http://') or path.startswith('https://'):
        return path
    return u'{static}img/{folder}{path}{extension}{version}'.format(
        static=RAW_CONTEXT['static_url'],
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
