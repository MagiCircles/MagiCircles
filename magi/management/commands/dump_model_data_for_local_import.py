import sys # at the end remove
from django.conf import settings as django_settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db.models import Prefetch
from django.db.models.fields import FieldDoesNotExist, related
from django.db.models.fields.files import ImageField
from magi.utils import modelHasField
from magi import models as magi_models

def print_to_files(fileds, text):
    for filed in fileds:
        if filed:
            filed.write(text)

def get_fields(model):
    fields = []
    foreign_keys = {}
    many_to_many = {}
    unique_fields = []
    for field_name in model._meta.get_all_field_names():
        if field_name.startswith('_cache_'):
            continue
        if field_name in ['id', 'owner']:
            continue
        try:
            field = model._meta.get_field(field_name)
            if isinstance(field, related.ForeignKey):
                if field.rel.to != model: # Avoid circular dependencies
                    foreign_keys[field_name] = field.rel.to
            elif isinstance(field, related.ManyToManyField):
                many_to_many[field_name] = field.rel.to
            else:
                if field.unique:
                    unique_fields.append(field_name)
                else:
                    fields.append(field_name)
        except FieldDoesNotExist:
            pass
    if not unique_fields:
        unique_fields = ['pk']
    return fields, unique_fields, foreign_keys, many_to_many

def dump_dependencies_getters(fileds, foreign_key_model, dependency_item, unique_fields, m2m_fields=None):
    fk_var_name = u'fk_{}_{}'.format(foreign_key_model.__name__, dependency_item.pk)
    if m2m_fields:
        # Allowed to be created (for non-collection models in m2m only without fk and m2m)
        m2m_fields, m2m_unique_fields, m2m_foreign_keys, m2m_many_to_many = m2m_fields
        if not m2m_foreign_keys and not m2m_foreign_keys:
            dump_item(fileds, foreign_key_model, dependency_item, m2m_unique_fields, m2m_fields, {}, {}, {}, {})
        return fk_var_name
    # Otherwise, can only be gotten
    print_to_files(fileds, u'try: {}\nexcept NameError:\n  try: {} = {}.{}.objects.get(**{})\n  except ObjectDoesNotExist: {} = None\n\n'.format(
        fk_var_name, fk_var_name,
        foreign_key_model.__module__,
        foreign_key_model.__name__,
        {
            key: getattr(dependency_item, key)
            for key in unique_fields
        },
        fk_var_name,
    ))
    return fk_var_name

def get_value(item, field):
    try:
        if isinstance(type(item)._meta.get_field(field), ImageField):
            return getattr(item, u'http_{}_url'.format(field))
    except FieldDoesNotExist:
        pass
    return getattr(item, field)

def dump_item(fileds, model, item, unique_fields, fields, foreign_keys, many_to_many, foreign_keys_unique_fields, m2m_can_be_created):
    data = { 'owner_id': 1 } if modelHasField(model, 'owner') else {}
    raw_data = {}
    unique_data = {}
    m2m_update = {}
    for foreign_key, foreign_key_model in foreign_keys.items():
        value = getattr(item, foreign_key)
        if value is not None:
            fk_var_name = dump_dependencies_getters(fileds, foreign_key_model, value, foreign_keys_unique_fields[foreign_key])
            raw_data[foreign_key] = fk_var_name
    for m2m, m2m_model in many_to_many.items():
        values = getattr(item, u'all_{}'.format(m2m))
        fk_var_names = []
        for value in values:
            fk_var_names.append(dump_dependencies_getters(fileds, m2m_model, value, foreign_keys_unique_fields[m2m], m2m_fields=m2m_can_be_created.get(m2m, None)))
        if fk_var_names:
            m2m_update[m2m] = u'[{}]'.format(u', '.join(fk_var_names))
    for field in unique_fields:
        value = get_value(item, field)
        if value is not None:
            unique_data[field] = str(value)
    for field in fields:
        value = get_value(item, field)
        if value is not None:
            data[field] = str(value)
    fk_var_name = 'fk_{}_{}'.format(model.__name__, item.pk)
    print_to_files(fileds, u'try: {fk_var_name}\nexcept NameError:\n'.format(fk_var_name=fk_var_name))
    lines_to_print_under_except = [
        u'data = {data}'.format(data=data),
    ]
    if raw_data:
        lines_to_print_under_except.append(
            u'data.update({dumped_raw_data})'.format(
                dumped_raw_data=u'{open_b}{dumped_raw_data}{close_b}'.format(
                    open_b=u'{',
                    dumped_raw_data=u','.join([
                        u'"{key}": {value}'.format(key=key, value=value)
                        for key, value in raw_data.items()
                    ]),
                    close_b=u'}',
                ),
            )
        )
    lines_to_print_under_except += [
        u'try:',
        u'  {fk_var_name} = {model_from}.{model_name}.objects.get({unique_data})'.format(
            fk_var_name=fk_var_name,
            model_from=model.__module__,
            model_name=model.__name__,
            unique_data=u' | '.join([
                u'Q({key}={value})'.format(key=key, value=repr(value))
                for key, value in unique_data.items()
            ]),
        ),
        u'  {model_from}.{model_name}.objects.filter(pk={fk_var_name}.pk).update(**data)'.format(
            fk_var_name=fk_var_name,
            model_from=model.__module__,
            model_name=model.__name__,
        ),
        u'  {fk_var_name} = {model_from}.{model_name}.objects.get(pk={fk_var_name}.pk)'.format(
            fk_var_name=fk_var_name,
            model_from=model.__module__,
            model_name=model.__name__,
        ),
        u'  total_updated += 1',
        u'except ObjectDoesNotExist:',
        u'  data.update({unique_data})'.format(
            unique_data=unique_data,
        ),
        u'  {fk_var_name} = {model_from}.{model_name}.objects.create(**data)'.format(
            fk_var_name=fk_var_name,
            model_from=model.__module__,
            model_name=model.__name__,
        ),
        u'  total_created += 1',
    ]
    if m2m_update:
        for key, value in m2m_update.items():
            lines_to_print_under_except.append(
                u'{fk_var_name}.{key} = {value}'.format(
                    fk_var_name=fk_var_name,
                    key=key, value=value,
                )
            )
        lines_to_print_under_except.append(
            u'{fk_var_name}.save()'.format(fk_var_name=fk_var_name)
        )
    print_to_files(fileds, u'{}\n\n'.format(u'\n'.join([
        u'  {}'.format(line)
        for line in lines_to_print_under_except
    ])))

def print_file_headers(filed):
    print_to_files([filed], u'from django.core.exceptions import ObjectDoesNotExist\n')
    print_to_files([filed], u'from django.db.models import Q\n')
    print_to_files([filed], u'from magi.tools import get_default_owner\n')
    print_to_files([filed], u'import magi, {}\n\n'.format(django_settings.SITE))
    print_to_files([filed], u'owner = get_default_owner()\n\n')
    print_to_files([filed], u'total_created = 0\ntotal_updated = 0\n\n')

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args) < 1:
            print '[model name]+'
            return

        custom_models = __import__(django_settings.SITE + '.models', fromlist=['']).__dict__

        global_filename = u'/tmp/dump.py'
        if len(args) > 1:
            global_filed = open(global_filename, 'w')
            print_file_headers(global_filed)
        else:
            global_filed = None

        for model_name in args:

            print '#', model_name

            model = getattr(magi_models, model_name, None)
            model = custom_models.get(model_name, model)
            if not model:
                print '  Model not found', model_name
                continue

            fields, unique_fields, foreign_keys, many_to_many = get_fields(model)

            print ''
            print '  Unique fields:', unique_fields
            print '  Fields found:', fields
            if foreign_keys:
                print '  Foreign keys found:', foreign_keys.keys()
            if many_to_many:
                print '  Many to many found:', many_to_many.keys()

            filename = u'/tmp/dump_{}.py'.format(model.__name__)
            filed = open(filename, 'w')
            fileds = [filed, global_filed]

            print_file_headers(filed)

            total_dumped = 0

            foreign_keys_unique_fields = {}
            m2m_can_be_created = {}
            for foreign_key, foreign_key_model in foreign_keys.items():
                all_fields = get_fields(foreign_key_model)
                foreign_keys_unique_fields[foreign_key] = all_fields[1]
            for m2m, m2m_model in many_to_many.items():
                all_fields = get_fields(m2m_model)
                foreign_keys_unique_fields[m2m] = all_fields[1]
                if not getattr(m2m_model, 'collection_name', None):
                    m2m_can_be_created[m2m] = all_fields

            if m2m_can_be_created:
                print '  The following m2m may be created if needed:', m2m_can_be_created.keys()
            print ''

            for item in model.objects.all().select_related(*foreign_keys.keys()).prefetch_related(*[
                    Prefetch(m2m, to_attr=u'all_{}'.format(m2m))
                    for m2m in many_to_many
            ]):
                dump_item(fileds, model, item, unique_fields, fields, foreign_keys, many_to_many, foreign_keys_unique_fields, m2m_can_be_created)
                total_dumped += 1

            print_to_files(fileds, u'print \'#\', {}\n'.format(repr(model.__name__)))
            print_to_files(fileds, u'print \'  Total created:\', total_created\n')
            print_to_files(fileds, u'print \'  Total updated:\', total_updated\n')

            filed.close()

            print '  Total dumped:', total_dumped
            print '  See file:', filename
            print ''


        if global_filed:
            global_filed.close()
            print 'Global file: ', global_filename
