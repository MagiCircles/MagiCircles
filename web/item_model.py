from collections import OrderedDict
from django.db import models
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _, get_language
from web.utils import tourldash, getMagiCollection

"""
Will not check if the views are enabled.
If you'd like to check, you can do:
  ```
  if instance.collection.item_view.enabled and instance.collection.item_view.ajax:
    return instance.collection.item_view_url
  ```
Checking adds a significant cost since it accesses the collection, so only do it when necessary.
"""

############################################################
# Get collection

def get_collection(instance):
    return getMagiCollection(instance.collection_name)

############################################################
# Get URLs

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

def get_image_url_from_path(imagePath):
    if not imagePath:
        return None
    imageURL = unicode(imagePath)
    #return u'{}{}'.format('//i.cinderella.pro/', imageURL)
    if '//' in imageURL:
        return imageURL
    if imageURL.startswith(django_settings.SITE + '/'):
        imageURL = imageURL.replace(django_settings.SITE + '/', '')
    return u'{}{}'.format(django_settings.SITE_STATIC_URL, imageURL)

def get_image_url(instance):
    return get_image_url_from_path(getattr(instance, 'image'))

def get_http_image_url_from_path(imagePath):
    imageURL = get_image_url_from_path(imagePath)
    if not imageURL:
        return None
    if 'http' not in imageURL:
        imageURL = 'http:' + imageURL
    return imageURL

def get_http_image_url(instance):
    return get_http_image_url_from_path(getattr(instance, 'image'))

def get_edit_url(instance):
    return u'/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

def get_report_url(instance):
    return u'/reports/add/{}/?id={}'.format(instance.collection_name, instance.pk)

def get_ajax_edit_url(instance):
    return u'/ajax/{}/edit/{}/'.format(instance.collection_plural_name, instance.pk)

############################################################
# Get sentences

def get_open_sentence(instance):
    return _('Open {thing}').format(thing=unicode(instance.collection.title).lower())

def get_edit_sentence(instance):
    return _('Edit {thing}').format(thing=unicode(instance.collection.title).lower())

def get_delete_sentence(instance):
    return _('Delete {thing}').format(thing=unicode(instance.collection.title).lower())

def get_report_sentence(instance):
    return _('Report {thing}').format(thing=unicode(instance.collection.title).lower())

def get_collection_plural_name(instance):
    if not getattr(instance, '_collection_plural_name', None):
        instance._collection_plural_name = instance.collection.plural_name
    return instance._collection_plural_name

############################################################
# Transform an existing model to an ItemModel
# Used for the User model

def addItemModelProperties(modelClass, collection_name):
    """
    Takes an existing Model class and adds the missing properties that would make it a proper ItemModel.
    Useful if you can't write a certain model yourself but you wish to use a MagiCollection for that model.
    """
    modelClass.collection_name = collection_name
    modelClass.collection = property(get_collection)
    modelClass.collection_plural_name = property(get_collection_plural_name)
    modelClass.item_url = property(get_item_url)
    modelClass.ajax_item_url = property(get_ajax_item_url)
    modelClass.full_item_url = property(get_full_item_url)
    modelClass.http_item_url = property(get_http_item_url)
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

############################################################
# ItemModel

class ItemModel(models.Model):
    collection_name = ''

    collection = property(get_collection)
    collection_plural_name = property(get_collection_plural_name)
    item_url = property(get_item_url)
    ajax_item_url = property(get_ajax_item_url)
    full_item_url = property(get_full_item_url)
    http_item_url = property(get_http_item_url)
    edit_url = property(get_edit_url)
    report_url = property(get_report_url)
    ajax_edit_url = property(get_ajax_edit_url)
    image_url = property(get_image_url)
    http_image_url = property(get_http_image_url)
    open_sentence = property(get_open_sentence)
    edit_sentence = property(get_edit_sentence)
    delete_sentence = property(get_delete_sentence)
    report_sentence = property(get_report_sentence)
    tinypng_settings = {}

    class Meta:
        abstract = True
