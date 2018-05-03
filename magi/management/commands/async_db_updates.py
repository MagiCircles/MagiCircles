# -*- coding: utf-8 -*-
import inspect, datetime, requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from django.db import models
from django.db.models import Q
from magi.item_model import BaseMagiModel
from magi.utils import modelHasField
from magi import models as magi_models

# All callbacks return True or False whether or not they did something
# When the first callback does something, the script stops

def update_image(model, field):
    if hasattr(model, u'_original_{}'.format(field.name)):
        print 'todo convert with tinypng async'
        return True
    if hasattr(model, u'_thumbnail_{}'.format(field.name)):
        print 'todo generate a thumbnail with tinypng'
        return True
    if hasattr(model, u'_2x_{}'.format(field.name)):
        print 'todo generate a 2x version with waifux2'
        return True
    return False

def update_markdown(model, field):
    if modelHasField(model, u'_cache_{}'.format(field.name[2:])):
        try:
            item = model.objects.exclude(
                Q(**{ u'{}__isnull'.format(field.name): True })
                | Q(**{ field.name: '' })
            ).filter(
                Q(**{ u'_cache_{}__isnull'.format(field.name[2:]): True })
                | Q(**{ u'_cache_{}'.format(field.name[2:]): '' })
            )[0]
        except IndexError:
            return False
        print u'Updating markdown {} for {} #{}...'.format(field.name, model.__name__, item.id)
        r = requests.post(
            u'https://api.github.com/markdown/raw',
            data=getattr(item, field.name).encode('utf-8'),
            headers={ 'content-type': u'text/plain' },
        )
        r.raise_for_status()
        model.objects.filter(id=item.id).update(**{
            u'_cache_{}'.format(field.name[2:]): r.text,
        })
        print 'Done.'
        return True
    return False

field_type_to_action = [
    (models.ImageField, update_image),
]

field_prefix_to_action = [
    ('m_', update_markdown),
]

def model_async_update(model):
    if inspect.isclass(model) and issubclass(model, BaseMagiModel):
        for field in model._meta.fields:
            for type_of_field, callback in field_type_to_action:
                if isinstance(field, type_of_field):
                    if callback(model, field):
                        return True
            for prefix, callback in field_prefix_to_action:
                if field.name.startswith(prefix):
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

        print datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        for model in magi_models.__dict__.values():
            if model_async_update(model):
                return

        custom_models = __import__(django_settings.SITE + '.models', fromlist=['']).__dict__
        for model in custom_models.values():
            if model_async_update(model):
                return

        print 'Nothing to do'
