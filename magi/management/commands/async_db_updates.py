# -*- coding: utf-8 -*-
import inspect, datetime, requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from django.db import models
from django.db.models import Q
from magi import urls # Unused, ensures RAW_CONTEXT to be filled
from magi.item_model import BaseMagiModel
from magi.models import uploadItem
from magi.utils import modelHasField, shrinkImageFromData, imageThumbnailFromData
from magi import models as magi_models

def get_next_item(model, field, modified_field_name, boolean_on_change=None):
    try:
        queryset = model.objects.all()

        if boolean_on_change is not None:
            # Field (boolean) = boolean_on_change
            # Modified field = NOT NULL
            queryset = queryset.filter(**{
                field.name: boolean_on_change,
            }).exclude(
                Q(**{ u'{}__isnull'.format(modified_field_name): True })
                | Q(**{ modified_field_name: '' })
            )
        else:
            # Field = NOT NULL
            # Modified field = NULL
            queryset = queryset.exclude(
                Q(**{ u'{}__isnull'.format(field.name): True })
                | Q(**{ field.name: '' })
            ).filter(
                Q(**{ u'{}__isnull'.format(modified_field_name): True })
                | Q(**{ modified_field_name: '' })
            )

        return queryset[0]

    except IndexError:
        return False

def save_item(model, item, updated_fields, in_item=False):
    if in_item:
        for k, v in updated_fields.items():
            setattr(item, k, v)
        item.save()
    else:
        model.objects.filter(id=item.pk).update(**updated_fields)

# All callbacks return True or False whether or not they did something
# When the first callback does something, the script stops

def update_image(model, field):
    if field.name.startswith('_'):
        return False
    tinypng_api_key = getattr(django_settings, 'TINYPNG_API_KEY', None)
    if tinypng_api_key and modelHasField(model, u'_original_{}'.format(field.name)):
        if tinypng_compress(model, field):
            return True
    if tinypng_api_key and modelHasField(model, u'_tthumbnail_{}'.format(field.name)):
        if tinypng_thumbnail(model, field):
            return True
    if modelHasField(model, u'_thumbnail_{}'.format(field.name)):
        if thumbnail(model, field):
            return True
    return False
    if modelHasField(model, u'_2x_{}'.format(field.name)):
        if thumbnail(model, field):
            return True
        print 'todo generate a 2x version with waifux2'
        return True
    return False

def tinypng_compress(model, field):
    original_field_name = u'_original_{}'.format(field.name)
    item = get_next_item(model, field, original_field_name)
    if not item:
        return False
    print '[Info] Compressing on TinyPNG {} for {} #{}...'.format(
        field.name, model.__name__, item.pk
    )
    value = getattr(item, field.name)
    filename = value.name
    content = value.read()
    if not content:
        save_item(model, item, { original_field_name: unicode(value) })
        print '[Warning] Empty file, discarded.'
        return True
    image = shrinkImageFromData(content, filename, settings=getattr(item, 'tinypng_settings', {}).get(field.name, {}))
    prefix = field.upload_to.prefix + ('tiny' if field.upload_to.prefix.endswith('/') else '/tiny')
    image.name = uploadItem(prefix)(item, filename)
    save_item(model, item, {
        original_field_name: unicode(value),
        field.name: image,
    }, in_item=True)
    print '[Info] Done.'
    return True

def tinypng_thumbnail(model, field):
    thumbnail_field_name = u'_tthumbnail_{}'.format(field.name)
    item = get_next_item(model, field, thumbnail_field_name)
    if not item:
        return False
    print '[Info] Generating thumbnail with TinyPNG {} for {} #{}...'.format(
        field.name, model.__name__, item.pk,
    )
    value = getattr(item, field.name)
    filename = value.name
    prefix = field.upload_to.prefix + ('thumb' if field.upload_to.prefix.endswith('/') else '/thumb')
    image_name = uploadItem(prefix)(item, filename)
    content = value.read()
    if not content:
        save_item(model, item, { thumbnail_field_name: unicode(value) })
        print '[Warning] Empty file, discarded.'
        return True
    tinypng_settings = getattr(item, 'tinypng_settings', {}).get(thumbnail_field_name, {}).copy()
    for k, v in [
            ('resize', 'thumb'),
            ('width', 200),
            ('height', 200),
    ]:
        if k not in tinypng_settings:
            tinypng_settings[k] = v
    image = shrinkImageFromData(content, image_name, settings=tinypng_settings)
    image.name = image_name
    save_item(model, item, { thumbnail_field_name: image }, in_item=True)
    print '[Info] Done.'
    return True

def thumbnail(model, field):
    thumbnail_field_name = u'_thumbnail_{}'.format(field.name)
    item = get_next_item(model, field, thumbnail_field_name)
    if not item:
        return False
    print '[Info] Generating a thumbnail {} for {} #{}...'.format(
        field.name, model.__name__, item.pk,
    )
    value = getattr(item, field.name)
    filename = value.name
    prefix = field.upload_to.prefix + ('thumb' if field.upload_to.prefix.endswith('/') else '/thumb')
    image_name = uploadItem(prefix)(item, filename)
    content = value.read()
    if not content:
        save_item(model, item, { thumbnail_field_name: unicode(value) })
        print '[Warning] Empty file, discarded.'
        return True
    thumbnail_size = getattr(model, 'thumbnail_size', {}).get(field.name, {}).copy()
    image = imageThumbnailFromData(content, image_name, width=thumbnail_size.get('width', 200), height=thumbnail_size.get('height', 200))
    image.name = image_name
    save_item(model, item, { thumbnail_field_name: image }, in_item=True)
    print '[Info] Done.'
    return True

def update_markdown(model, field):
    if modelHasField(model, u'_cache_{}'.format(field.name[2:])):
        item = get_next_item(model, field, u'_cache_{}'.format(field.name[2:]))
        if not item:
            return False
        print u'[Info] Updating markdown {} for {} #{}...'.format(field.name, model.__name__, item.pk)
        r = requests.post(
            u'https://api.github.com/markdown/raw',
            data=getattr(item, field.name).encode('utf-8'),
            headers={ 'content-type': u'text/plain' },
        )
        r.raise_for_status()
        save_item(model, item, {
            u'_cache_{}'.format(field.name[2:]): r.text,
        })
        print '[Info] Done.'
        return True
    return False

def update_on_change(model, field):
    if isinstance(field, models.BooleanField) and hasattr(model, u'{}_ON_CHANGE'.format(field.name[:8].upper())):
        item = get_next_item(model, field, field.name[:8], boolean_on_change=True)
        if not item:
            return False
        print u'[Info] Updating {} after change occured for {} #{}...'.format(field.name[:8], model.__name__, item.pk)
        callback = getattr(model, u'{}_ON_CHANGE'.format(field.name[:8].upper()))
        if callback(item):
            print '[Info] Done.'
            return True
    return False

field_type_to_action = [
    (models.ImageField, update_image),
]

field_prefix_to_action = [
    ('m_', update_markdown),
]

field_suffix_to_action = [
    ('_changed', update_on_change),
]

def model_async_update(model, specified_model=None, field_name=None):
    if (inspect.isclass(model)
        and issubclass(model, BaseMagiModel)
        and not getattr(model._meta, 'abstract', False)
        and (not specified_model or model.__name__ == specified_model)):
        for field in model._meta.fields:
            if field_name and field.name != field_name:
                continue
            for type_of_field, callback in field_type_to_action:
                if isinstance(field, type_of_field):
                    if callback(model, field):
                        return True
            for prefix, callback in field_prefix_to_action:
                if field.name.startswith(prefix):
                    if callback(model, field):
                        return True
            for suffix, callback in field_suffix_to_action:
                if field.name.endswith(suffix):
                    if callback(model, field):
                        return True
    return False

class Command(BaseCommand):
    """
    Performs one asynchronous operation among the default ones, such as:
    - Caches the markdown version of a m_something field
    - Uses TinyPNG to optimize an image and keep the original in _original_something if field exists
    - Create a thumbbail in _thumbnail_something if field exists
    - Generate a 2x version with waifux2 in _2x_something if field exists
    """
    can_import_settings = True

    def handle(self, *args, **options):

        print '[Info]', datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        try: specified_model = args[0]
        except IndexError: specified_model = None

        try: specified_field_name = args[1]
        except IndexError: specified_field_name = None

        for model in magi_models.__dict__.values():
            if model_async_update(model, specified_model=specified_model, field_name=specified_field_name):
                return

        custom_models = __import__(django_settings.SITE + '.models', fromlist=['']).__dict__
        for model in custom_models.values():
            if model_async_update(model, specified_model=specified_model, field_name=specified_field_name):
                return

        print '[Info] Nothing to do'
