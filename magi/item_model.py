import json, datetime
from collections import OrderedDict
from django.contrib.auth.models import User
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _, get_language
from django.utils import timezone
from magi.utils import tourldash, getMagiCollection, join_data, split_data, AttrDict, getSubField

############################################################
# Utils for images / files

def get_file_url_from_path(filePath):
    if not filePath:
        return None
    fileURL = unicode(filePath)
    if '//' in fileURL:
        return fileURL
    if fileURL.startswith(django_settings.SITE + '/'):
        fileURL = fileURL.replace(django_settings.SITE + '/', '')
    return u'{}{}'.format(django_settings.SITE_STATIC_URL, fileURL)

def get_file_url(instance, file_name='file'):
    return get_file_url_from_path(getattr(instance, file_name))

def get_http_file_url_from_path(filePath):
    fileURL = get_file_url_from_path(filePath)
    if not fileURL:
        return None
    if 'http' not in fileURL:
        fileURL = u'https:' + fileURL
    return fileURL

def get_http_file_url(instance, file_name='file'):
    return get_http_file_url_from_path(getattr(instance, file_name))

get_image_url_from_path = get_file_url_from_path
get_image_url = get_file_url
get_http_image_url_from_path = get_http_file_url_from_path
get_http_image_url = get_http_file_url

############################################################
# Utils for choices

def i_choices(choices, translation=True):
    if not choices:
        return []
    return [(i, choice[1 if translation else 0] if isinstance(choice, tuple) else choice) for i, choice in enumerate(choices)]

def getInfoFromChoices(field_name, details, key):
    def _getInfo(instance):
        value = getattr(instance, field_name)
        if (not value
            or value not in details
            or key not in details[value]):
            return None
        return details[value][key]
    return _getInfo

############################################################
# Utils for owner

def get_selector_to_owner(cls):
    if cls.fk_as_owner:
        return u'{}__owner'.format(cls.fk_as_owner)
    return 'owner'

def get_owners_queryset(cls, user):
    if not cls.fk_as_owner:
        return [user]
    return cls._meta.get_field(cls.fk_as_owner).rel.to.objects.filter(**{
        cls.selector_to_owner()[(len(cls.fk_as_owner) + 2):]:
        user,
    })

def get_owner_ids(cls, user):
    if cls.fk_as_owner:
        return list(cls.owners_queryset(user).values_list('id', flat=True))
    return [user.id]

def get_owner_collection(cls):
    if cls.fk_as_owner:
        return getMagiCollection(cls.fk_as_owner)
    return getMagiCollection('user')

def get_allow_multiple_per_owner(cls):
    # todo
    print cls.owner
    return cls.owner

def get_is_owner(instance, user):
    return user and instance.owner_id == user.id

def get_owner_unicode(instance):
    if instance.fk_as_owner:
        fk_as_owner = getattr(instance, u'cached_{}'.format(instance.fk_as_owner))
        if not fk_as_owner:
            fk_as_owner = getattr(instance, instance.fk_as_owner)
        return fk_as_owner.unicode if hasattr(fk_as_owner, 'unicode') else unicode(fk_as_owner)
    return instance.owner.unicode if hasattr(instance.owner, 'unicode') else unicode(instance.owner)

def get_real_owner(instance):
    """
    In case of a cached owner, ensure the retriaval of the actual owner object.
    Performs extra query, use with caution.
    """
    if isinstance(instance, User):
        return instance
    if isinstance(instance.__class__.owner, property):
        if not getattr(instance, '_real_owner', None) or True:
            instance._real_owner = getSubField(type(instance).objects.select_related(instance.selector_to_owner()).get(id=instance.id), instance.selector_to_owner().split('__'))
        return instance._real_owner
    return instance.owner

############################################################
# BaseMagiModel

class BaseMagiModel(models.Model):
    """
    Can be used for your models that don't have an associated MagiCollection.

    It comes with:
    - helpers for owner
    - helpers for i_ fields
      - i_something: raw integer value
      - something: string representation
      - t_something: i18n string representation
    - helpers for images
      - image_url, http_image_url where "image" is the name of the image field
    - tinypng_settings
    - helpers for CSV values
      - c_something: raw string
      - something: list of CSV values
      - t_something: list of translated values
      - add_c: add some new strings in the list
      - remove_c: remove some strings from the list
      - save_c: replace the full list of existing strings
    """
    tinypng_settings = {}

    fk_as_owner = None
    selector_to_owner = classmethod(get_selector_to_owner)
    owners_queryset = classmethod(get_owners_queryset)
    owner_ids = classmethod(get_owner_ids)
    allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    owner_collection = classmethod(get_owner_collection)
    is_owner = get_is_owner
    owner_unicode = property(get_owner_unicode)
    real_owner = property(get_real_owner)

    @classmethod
    def get_choices(self, field_name):
        """
        Return value is a list of tuples with:
           (int, (string, translated string))
        or (int, string)
        """
        try:
            choices = getattr(self, '{name}_CHOICES'.format(name=field_name.upper()))
            if getattr(self, u'{name}_WITHOUT_I_CHOICES'.format(name=field_name.upper()), False):
                return [(c[0], c) for c in choices]
            return list(enumerate(choices))
        except AttributeError:
            return list(self._meta.get_field('i_{name}'.format(name=field_name)).choices)

    @classmethod
    def get_i(self, field_name, string):
        """
        Takes a string value of a choice and return its internal value
        field_name = without i_
        """
        try:
            return next(
                index
                for index, c in self.get_choices(field_name)
                if (c[0] if isinstance(c, tuple) else c) == string
            )
        except StopIteration:
            if string is None:
                return None
            raise KeyError(string)

    @classmethod
    def get_reverse_i(self, field_name, i):
        """
        Takes an int value of a choice and return its string value
        field_name = without i_
        """
        try:
            return next(
                (c[0] if isinstance(c, tuple) else c)
                for index, c in self.get_choices(field_name)
                if index == i
            )
        except StopIteration:
            if i is None:
                return None
            raise KeyError(i)

    @classmethod
    def get_verbose_i(self, field_name, i):
        """
        Takes an int value of a choice and return its verbose value
        field_name = without i_
        """
        try:
            return next(
                (c[1] if isinstance(c, tuple) else c)
                for index, c in self.get_choices(field_name)
                if index == i
            )
        except StopIteration:
            if i is None:
                return None
            raise KeyError(i)

    @classmethod
    def get_csv_values(self, field_name, values, translated=True):
        if not isinstance(values, list):
            values = split_data(values)
        if not translated:
            return values
        choices = {
            (choice[0] if isinstance(choice, tuple) else choice):
            (choice[1] if isinstance(choice, tuple) else _(choice))
            for choice in getattr(self, '{name}_CHOICES'.format(name=field_name.upper()), [])
        }
        return OrderedDict([(c, choices.get(c, c)) for c in values])

    @classmethod
    def get_dict_values(self, field_name, values, translated):
        if not values: return {}
        d = json.loads(values)
        if not translated:
            return d
        choices = {
            (choice[0] if isinstance(choice, tuple) else choice):
            (choice[1] if isinstance(choice, tuple) else _(choice))
            for choice in getattr(self, u'{name}_CHOICES'.format(name=field_name.upper()), [])
        }
        return {
            key: {
                'value': value,
                'verbose': choices.get(key, key),
            } for key, value in d.items()
        }

    @classmethod
    def get_json_value(self, field_name, value):
        if not value: return None
        return json.loads(value)

    @classmethod
    def cached_json_extra(self, field_name, d):
        # Get original model class for cached thing
        try: original_cls = self._meta.get_field(field_name).rel.to
        except FieldDoesNotExist: original_cls = None
        original_cls = getattr(self, u'_cache_{}_fk_class'.format(field_name), original_cls)
        if callable(original_cls): original_cls = original_cls()

        # Call pre if provided
        if hasattr(self, u'cached_{}_pre'.format(field_name)):
            getattr(self, u'cached_{}_pre'.format(field_name))(d)

        # Add default unicode if missing
        if 'unicode' not in d:
            d['unicode'] = d['name'] if 'name' in d else (d['id'] if 'id' in d else '?')

        # TODO try to add a way to call __unicode__ smooth

        if 'id' in d:
            if 'pk' not in d:
                d['pk'] = d['id']
            # Set collection item URLs
            collection_name = getattr(self, u'_cached_{}_collection_name'.format(field_name), field_name)
            if 'item_url' not in d:
                d['item_url'] = u'/{}/{}/{}/'.format(collection_name, d['id'], tourldash(d['unicode']))
            if 'ajax_item_url' not in d:
                d['ajax_item_url'] = u'/ajax/{}/{}/'.format(collection_name, d['id'])
            if 'full_item_url' not in d:
                d['full_item_url'] = u'{}{}/{}/{}/'.format(django_settings.SITE_URL, collection_name, d['id'], tourldash(d['unicode']))
            if 'http_item_url' not in d:
                d['http_item_url'] = u'https:{}'.format(d['full_item_url']) if 'http' not in d['full_item_url'] else d['full_item_url']

        # Set image url helpers
        if 'image' in d:
            if 'image_url' not in d:
                d['image_url'] = get_image_url_from_path(d['image'])
            if 'http_image_url' not in d:
                d['http_image_url'] = get_http_image_url_from_path(d['image'])

        if original_cls:
            for k in d.keys():
                # i_ fields
                if k.startswith('i_'):
                    d[k[2:]] = original_cls.get_reverse_i(k[2:], d[k])
                    d['t_{}'.format(k[2:])] = original_cls.get_verbose_i(k[2:], d[k])

        # Call extra if provided
        if hasattr(self, u'cached_{}_extra'.format(field_name)):
            getattr(self, u'cached_{}_extra'.format(field_name))(d)
        return d

    @classmethod
    def get_cached_json(self, field_name, value):
        if value is None: return None
        d = json.loads(value)
        if d is None: return None
        if isinstance(d, list):
            d = map(lambda _d: AttrDict(self.cached_json_extra(field_name, _d)), d)
        else:
            d = AttrDict(self.cached_json_extra(field_name, d))
        return d

    @classmethod
    def get_cached_csv(self, field_name, value):
        if value is None: return []
        values = split_data(value)
        map_method = getattr(self, u'cached_{}_map'.format(field_name), None)
        return [map_method(i) for i in values] if map_method else values

    def _get_markdown_value(self, field_name):
        html = getattr(self, u'_cache_{}'.format(field_name))
        if html:
            return True, html
        markdown = getattr(self, u'm_{}'.format(field_name))
        return False, markdown

    def add_c(self, field_name, to_add):
        """
        Add strings from a CSV formatted c_something
        """
        current_c = getattr(self, field_name)
        setattr(self, 'c_{name}'.format(name=field_name),
                join_data(*(current_c + [c for c in to_add if c not in current_c])))

    def remove_c(self, field_name, to_remove):
        """
        Remove strings to a CSV formatted c_something
        """
        current_c = getattr(self, field_name)
        setattr(self, 'c_{name}'.format(name=field_name),
                join_data(*[c for c in current_c if c not in to_remove]))

    def save_c(self, field_name, c):
        """
        Completely replace any existing CSV formatted list into c_something
        """
        setattr(self, 'c_{name}'.format(name=field_name), join_data(*c))

    def add_d(self, field_name, key, value):
        current_d = getattr(self, field_name)
        current_d[key] = value
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(current_d))

    def remove_d(self, field_name, key):
        current_d = getattr(self, field_name)
        del(current_d[key])
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(current_d) if current_d else None)

    def save_d(self, field_name, d):
        setattr(self, u'd_{name}'.format(name=field_name), json.dumps(d) if d else None)

    def save_j(self, field_name, j):
        setattr(self, u'j_{name}'.format(name=field_name), json.dumps(j) if j else None)

    def force_update_cache(self, field_name):
        self.update_cache(field_name)
        self.save()

    def update_cache(self, field_name):
        to_cache_method = getattr(self, u'to_cache_{}'.format(field_name), None)
        if not to_cache_method:
            raise NotImplementedError(u'to_cache_{f} method is required for {f} cache'.format(f=field_name))
        setattr(self, u'_cache_{}_last_update'.format(field_name), timezone.now())
        value = to_cache_method()
        if hasattr(self, '_cache_j_{}'.format(field_name)):
            value = json.dumps(value) if value else None
            setattr(self, u'_cache_j_{}'.format(field_name), value)
        elif hasattr(self, '_cache_c_{}'.format(field_name)):
            value = join_data(*value) if value else None
            setattr(self, u'_cache_c_{}'.format(field_name), value)
        setattr(self, u'_cache_{}'.format(field_name), value)

    def _force_on_last_update_or_none(self, field_name, prefix=''):
        days = getattr(self, u'_cache_{}_days'.format(field_name), None)
        if days and hasattr(self, u'_cache_{}_last_update'.format(field_name)):
            last_update = getattr(self, u'_cache_{}_last_update'.format(field_name), None)
            if not last_update or last_update < timezone.now() - datetime.timedelta(days=days):
                self.force_update_cache(field_name)
        if (getattr(self, u'_cache_{}_update_on_none'.format(field_name), False)
            and getattr(self, u'_cache_{}{}'.format(prefix, field_name)) is None):
            self.force_update_cache(field_name)

    def __getattr__(self, name):
        # For choice fields with name "i_something", accessing "something" returns the string value
        if not name.startswith('_') and not name.startswith('i_') and not name.startswith('c_') and not name.startswith('m_') and not name.startswith('d_') and not name.startswith('j_'):
            # When accessing "something" and "i_something exists, return the readable key for the choice
            if hasattr(self, u'i_{name}'.format(name=name)):
                return type(self).get_reverse_i(name, getattr(self, u'i_{name}'.format(name=name)))
            # When accessing "t_something", return the verbose value
            elif name.startswith('t_'):
                name = name[2:]
                # For a i_choice
                if hasattr(self, 'i_{name}'.format(name=name)):
                    return type(self).get_verbose_i(name, getattr(self, 'i_{name}'.format(name=name)))
                # For a CSV value: return dict {value: translated value}
                elif hasattr(self, 'c_{name}'.format(name=name)):
                    return type(self).get_csv_values(name, getattr(self, name))
                # For a dict: return dict {key: {'value': value, 'verbose': translation}}
                elif hasattr(self, u'd_{name}'.format(name=name)):
                    return type(self).get_dict_values(name, getattr(self, u'd_{name}'.format(name=name)), translated=True)
                # For a dict, if no _s exists: return value for language
                elif hasattr(self, u'd_{}s'.format(name)) and hasattr(self, name):
                    return getattr(self, u't_{name}s'.format(name=name)).get(get_language(), { 'value': getattr(self, name) })['value']
            # When accessing "something_url"
            elif name.endswith('_url'):
                field_name = name.replace('http_', '')[:-4]
                # For an image, return the url
                if isinstance(self._meta.get_field(field_name), models.ImageField):
                    return (get_http_image_url(self, field_name)
                            if name.startswith('http_')
                            else get_image_url(self, field_name))
                # For a file, return the url
                elif isinstance(self._meta.get_field(field_name), models.FileField):
                    return (get_http_file_url(self, field_name)
                            if name.startswith('http_')
                            else get_file_url(self, field_name))
            # When accessing "something" and "c_something" exists, returns the list of CSV values
            elif hasattr(self, 'c_{name}'.format(name=name)):
                return type(self).get_csv_values(name, getattr(self, 'c_{name}'.format(name=name)), translated=False)
            # When accessing "something" and "d_something" exists, returns the dict
            elif hasattr(self, 'd_{name}'.format(name=name)):
                return type(self).get_dict_values(name, getattr(self, u'd_{name}'.format(name=name)), translated=False)
            # When accessing "something" and "m_something" exists, returns the html value if exists
            elif hasattr(self, 'm_{name}'.format(name=name)):
                return self._get_markdown_value(name)
            # When accessing "something" and "j_something" exists, return the python variable (dict, list, ...)
            elif hasattr(self, u'j_{}'.format(name)):
                return type(self).get_json_value(name, getattr(self, u'j_{}'.format(name)))

        # Return cache
        if name.startswith('cached_'):
            field_name = name[7:]
            # Accessing cached_something when _cache_j_something exists
            if hasattr(self, '_cache_j_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name, prefix='j_')
                return type(self).get_cached_json(field_name, getattr(self, '_cache_j_{}'.format(field_name)))
            # Accessing cached_something when _cache_c_something exists
            elif hasattr(self, '_cache_c_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name, prefix='j_')
                return type(self).get_cached_csv(field_name, getattr(self, '_cache_c_{}'.format(field_name)))
            # Accessing cached_something when _cache_something exists
            elif hasattr(self, '_cache_{}'.format(field_name)):
                self._force_on_last_update_or_none(field_name)
                return getattr(self, '_cache_{}'.format(field_name))

        raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

    class Meta:
        abstract = True

############################################################
# Utils for collection (used by MagiModel and addMagiModelProperties)

############################################################
# Get collection

def get_collection(instance):
    return getMagiCollection(instance.collection_name)

############################################################
# Get URLs

# Will not check if the views are enabled.
# If you'd like to check, you can do:
#   ```
#   if instance.collection.item_view.enabled and instance.collection.item_view.ajax:
#     return instance.collection.item_view_url
#   ```
# Checking adds a significant cost since it accesses the collection, so only do it when necessary.

def get_item_url(instance):
    return u'/{}/{}/{}/'.format(instance.collection_name, instance.pk, tourldash(unicode(instance)))

def get_ajax_item_url(instance):
    return u'/ajax/{}/{}/'.format(instance.collection_name, instance.pk)

def get_full_item_url(instance):
    return u'{}{}/{}/{}/'.format(django_settings.SITE_URL, instance.collection_name, instance.pk, tourldash(unicode(instance)))

def get_http_item_url(instance):
    url = get_full_item_url(instance)
    if url and 'http' not in url:
        url = 'https:' + url
    return url

def get_share_url(instance):
    return instance.http_item_url

def get_edit_url(instance):
    return u'/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

def get_report_url(instance):
    return u'/reports/add/{}/?id={}'.format(instance.collection_name, instance.pk)

def get_ajax_edit_url(instance):
    return u'/ajax/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

############################################################
# Get sentences

def get_open_sentence(instance):
    return _('Open {thing}').format(thing=unicode(instance.collection_title).lower())

def get_edit_sentence(instance):
    return _('Edit {thing}').format(thing=unicode(instance.collection_title).lower())

def get_delete_sentence(instance):
    return _('Delete {thing}').format(thing=unicode(instance.collection_title).lower())

def get_report_sentence(instance):
    return _('Report {thing}').format(thing=unicode(instance.collection_title).lower())

def get_collection_plural_name(instance):
    if not getattr(instance, '_collection_plural_name', None):
        instance._collection_plural_name = instance.collection.plural_name
    return instance._collection_plural_name

def get_collection_title(instance):
    if not getattr(instance, '_collection_title', None):
        instance._collection_title = instance.collection.title
    return instance._collection_title

############################################################
# Transform an existing model to an MagiModel
# Used for the User model

def addMagiModelProperties(modelClass, collection_name):
    """
    Takes an existing Model class and adds the missing properties that would make it a proper MagiModel.
    Useful if you can't write a certain model yourself but you wish to use a MagiCollection for that model.
    Will not have the properties and tools provided by BaseMagiModel, except helpers for images, c_ and i_fields.
    """
    modelClass.collection_name = collection_name
    modelClass.collection = property(get_collection)
    modelClass.collection_plural_name = property(get_collection_plural_name)
    modelClass.collection_title = property(get_collection_title)
    modelClass.item_url = property(get_item_url)
    modelClass.ajax_item_url = property(get_ajax_item_url)
    modelClass.full_item_url = property(get_full_item_url)
    modelClass.http_item_url = property(get_http_item_url)
    modelClass.share_url = property(get_share_url)
    modelClass.edit_url = property(get_edit_url)
    modelClass.report_url = property(get_report_url)
    modelClass.ajax_edit_url = property(get_ajax_edit_url)
    modelClass.image_url = property(get_image_url)
    modelClass.http_image_url = property(get_http_image_url)
    modelClass.open_sentence = property(get_open_sentence)
    modelClass.edit_sentence = property(get_edit_sentence)
    modelClass.delete_sentence = property(get_delete_sentence)
    modelClass.report_sentence = property(get_report_sentence)
    modelClass.tinypng_settings = {}

    modelClass.fk_as_owner = None
    modelClass.selector_to_owner = classmethod(get_selector_to_owner)
    modelClass.owners_queryset = classmethod(get_owners_queryset)
    modelClass.owner_ids = classmethod(get_owner_ids)
    modelClass.allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    modelClass.owner_collection = classmethod(get_owner_collection)
    modelClass.is_owner = get_is_owner
    modelClass.owner_unicode = property(get_owner_unicode)
    modelClass.real_owner = property(get_real_owner)

############################################################
# MagiModel

class MagiModel(BaseMagiModel):
    """
    The model you must inherit from
    """
    collection_name = ''

    collection = property(get_collection)
    collection_plural_name = property(get_collection_plural_name)
    collection_title = property(get_collection_title)
    item_url = property(get_item_url)
    ajax_item_url = property(get_ajax_item_url)
    full_item_url = property(get_full_item_url)
    http_item_url = property(get_http_item_url)
    share_url = property(get_share_url)
    edit_url = property(get_edit_url)
    report_url = property(get_report_url)
    ajax_edit_url = property(get_ajax_edit_url)
    open_sentence = property(get_open_sentence)
    edit_sentence = property(get_edit_sentence)
    delete_sentence = property(get_delete_sentence)
    report_sentence = property(get_report_sentence)

    allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)

    def __unicode__(self):
        try:
            return unicode(self.collection_title)
        except AttributeError:
            return unicode(self.collection_name)

    class Meta:
        abstract = True
