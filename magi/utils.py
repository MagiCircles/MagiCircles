from __future__ import division
import os, string, random, csv, tinify, cStringIO, pytz, simplejson
from PIL import Image
from django.conf import settings as django_settings
from django.core.files.temp import NamedTemporaryFile
from django.core.urlresolvers import resolve
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _, get_language
from django.utils.formats import dateformat
from django.utils import timezone
from django.template import Context
from django.template.loader import get_template
from django.db import models
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms.models import model_to_dict
from django.forms import NullBooleanField
from django.core.mail import EmailMultiAlternatives
from django.core.files.images import ImageFile
from magi.middleware.httpredirect import HttpRedirectException
from magi.default_settings import RAW_CONTEXT

############################################################
# Favorite characters

FAVORITE_CHARACTERS_IMAGES = { id: image for (id, name, image) in getattr(django_settings, 'FAVORITE_CHARACTERS', []) }

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
# Helpers for MagiCollections

def justReturn(string):
    return lambda *args, **kwargs: string

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
    context['hidenavbar'] = 'hidenavbar' in request.GET
    context['request'] = request
    context['javascript_translated_terms_json'] = simplejson.dumps({ term: unicode(_(term)) for term in context['javascript_translated_terms']})
    context['localized_language'] = LANGUAGES_DICT.get(get_language(), '')
    cuteFormFieldsForContext({
        'language': {
            'selector': '#switchLanguage',
            'choices': django_settings.LANGUAGES,
        },
    }, context)
    return context

def getGlobalContext(request):
    if django_settings.GET_GLOBAL_CONTEXT:
        return django_settings.GET_GLOBAL_CONTEXT(request)
    return globalContext(request)

def ajaxContext(request):
    context = RAW_CONTEXT.copy()
    return context

def emailContext():
    context = RAW_CONTEXT.copy()
    if context['site_url'].startswith('//'):
        context['site_url'] = 'http:' + context['site_url']
    return context

class CuteFormType:
    Images, HTML, YesNo, OnlyNone = range(4)
    to_string = ['images', 'html', 'html', 'html']
    default_to_cuteform = ['key', 'value', 'value', 'value']

class CuteFormTransform:
    No, ImagePath, Flaticon, FlaticonWithText = range(4)
    default_field_type = [CuteFormType.Images, CuteFormType.Images, CuteFormType.HTML, CuteFormType.HTML]

def cuteFormFieldsForContext(cuteform_fields, context, form=None):
    """
    Adds the necesary context to call cuteform in javascript.
    cuteform_fields: must be a dictionary of {
      field_name: {
        type: CuteFormType.Images, .HTML, .YesNo or .OnlyNone, will be images if not specified,
        to_cuteform: 'key' or 'value' or lambda that takes key and value, will be 'key' if not specified,
        choices: list of pair, if not specified will use form
        selector: will be #id_{field_name} if not specified,
        transform: when to_cuteform is a lambda: CuteFormTransform.No, .ImagePath, .Flaticon, .FlaticonWithText
        image_folder: only when to_cuteform = 'images' or transform = 'images', will specify the images path,
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
        # Initialize cuteform dict for field
        context['cuteform_fields'][field['selector']] = {
            CuteFormType.to_string[field_type]: {},
        }
        # Add extra settings if any
        if 'extra_settings' in field:
            context['cuteform_fields'][field['selector']].update(field['extra_settings'])
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
                    cuteform = u'{static_url}img/{field_name}/{value}.png'.format(
                        static_url=context['static_url'],
                        field_name=field.get('image_folder', field_name),
                        value=unicode(cuteform_value),
                    )
                # Transform to flaticon
                elif transform in [CuteFormTransform.Flaticon, CuteFormTransform.FlaticonWithText]:
                    cuteform = u'<i class="flaticon-{icon}"></i>{text}'.format(
                        icon=cuteform_value,
                        text=u' {}'.format(value) if transform == CuteFormTransform.FlaticonWithText else '',
                    )
                else:
                    cuteform = unicode(cuteform_value)
            # Add in key, value in context for field
            context['cuteform_fields'][field['selector']][CuteFormType.to_string[field_type]][key] = cuteform

        # Store a JSON version to be displayed in Javascript
        context['cuteform_fields_json'][field['selector']] = simplejson.dumps(context['cuteform_fields'][field['selector']])

############################################################
# Database upload to

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

def redirectWhenNotAuthenticated(request, context, next_title=None):
    if not request.user.is_authenticated():
        if context.get('current_url', '').startswith('/ajax/'):
            raise HttpRedirectException(u'/signup/')
        raise HttpRedirectException(u'/signup/{}'.format((u'?next={}{}'.format(context['current_url'], u'&next_title={}'.format(unicode(next_title)) if next_title else u'')) if 'current_url' in context else ''))

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

############################################################
# Set a field in a sub dictionary

def setSubField(fields, field_name, value, key='icon'):
    if field_name in fields:
        fields[field_name][key] = value(field_name) if callable(value) else value

############################################################
# Join / Split data stored as string in database

def split_data(data):
    """
    Takes a unicode CSV string and return a list of strings.
    """
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def unicode_csv_reader(unicode_csv_data, **kwargs):
        csv_reader = csv.reader(utf_8_encoder(unicode_csv_data), **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    if not data:
        return []
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
# Use TinyPNG to optimize images

def dataToImageFile(data):
    image = NamedTemporaryFile(delete=False)
    image.write(data)
    image.flush()
    return ImageFile(image)

def shrinkImageFromData(data, filename, settings={}):
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
    try:
        data = source.to_buffer()
    except: # Retry without resizing
        try:
            data = tinify.from_buffer(data).to_buffer()
        except: # Just return the original data
            pass
    return dataToImageFile(data)

############################################################
# UserLink image URL

def linkToImageURL(link):
    return '{}img/links/{}.png'.format(RAW_CONTEXT['static_url'], link.i_type)
