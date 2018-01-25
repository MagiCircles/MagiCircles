from collections import OrderedDict
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _, get_language
from magi.utils import tourldash, getMagiCollection, join_data, split_data

############################################################
# Utils for images

def get_image_url_from_path(imagePath):
    if not imagePath:
        return None
    imageURL = unicode(imagePath)
    if '//' in imageURL:
        return imageURL
    if imageURL.startswith(django_settings.SITE + '/'):
        imageURL = imageURL.replace(django_settings.SITE + '/', '')
    return u'{}{}'.format(django_settings.SITE_STATIC_URL, imageURL)

def get_image_url(instance, image_name='image'):
    return get_image_url_from_path(getattr(instance, image_name))

def get_http_image_url_from_path(imagePath):
    imageURL = get_image_url_from_path(imagePath)
    if not imageURL:
        return None
    if 'http' not in imageURL:
        imageURL = 'http:' + imageURL
    return imageURL

def get_http_image_url(instance, image_name='image'):
    return get_http_image_url_from_path(getattr(instance, image_name))

############################################################
# Utils for choices

def i_choices(choices):
    if not choices:
        return []
    return [(i, choice[1] if isinstance(choice, tuple) else choice) for i, choice in enumerate(choices)]

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

def get_owner_ids(cls, user):
    if not user.is_authenticated():
        return []
    if cls.fk_as_owner:
        return cls.objects.filter(**{ cls.selector_to_owner(): user }).distinct().values_list(
            u'{}_id'.format(cls.fk_as_owner), flat=True)
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
    owner_ids = classmethod(get_owner_ids)
    allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    owner_collection = classmethod(get_owner_collection)
    is_owner = get_is_owner

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

    def __getattr__(self, name):
        # For choice fields with name "i_something", accessing "something" returns the string value
        if not name.startswith('_') and not name.startswith('i_') and not name.startswith('c_'):
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
                    return self._c_to_t(name)
            # When accessing "something_url" for an image, return the url
            elif name.endswith('_url'):
                field_name = name.replace('http_', '')[:-4]
                if isinstance(self._meta.get_field(field_name), models.ImageField):
                    return (get_http_image_url(self, field_name)
                            if name.startswith('http_')
                            else get_image_url(self, field_name))
            # When accessing "something" and "c_something" exists, returns the list of CSV values
            elif hasattr(self, 'c_{name}'.format(name=name)):
                return split_data(getattr(self, 'c_{name}'.format(name=name)))
        raise AttributeError("%r object has no attribute %r" % (self.__class__, name))

    def _c_to_t(self, name):
        choices = {
            (choice[0] if isinstance(choice, tuple) else choice):
            (choice[1] if isinstance(choice, tuple) else _(choice))
            for choice in getattr(self, '{name}_CHOICES'.format(name=name.upper()), [])
        }
        return OrderedDict([(c, choices.get(c, c)) for c in getattr(self, name)])

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
        url = 'http:' + url
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
    modelClass.owner_ids = classmethod(get_owner_ids)
    modelClass.allow_multiple_per_owner = classmethod(get_allow_multiple_per_owner)
    modelClass.owner_collection = classmethod(get_owner_collection)
    modelClass.is_owner = get_is_owner

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
            return self.collection_title
        except AttributeError:
            return self.collection_name

    class Meta:
        abstract = True
