from django.db import models
from django.conf import settings as django_settings
from web.utils import tourldash

def get_image_url(imagePath):
    if not imagePath:
        return None
    imageURL = unicode(imagePath)
    if '//' in imageURL:
        return imageURL
    if imageURL.startswith(django_settings.SITE + '/'):
        imageURL = imageURL.replace(django_settings.SITE + '/', '')
    return u'{}{}'.format(django_settings.SITE_STATIC_URL, imageURL)

def get_http_image_url(imagePath):
    imageURL = get_image_url(imagePath)
    if not imageURL:
        return None
    if 'http' not in imageURL:
        imageURL = 'http:' + imageURL
    return imageURL

def get_item_url(collection_name, instance):
    return u'/{}/{}/{}/'.format(collection_name, instance.pk, tourldash(unicode(instance)))

def get_ajax_item_url(collection_name, instance):
    return u'/ajax/{}/{}/'.format(collection_name, instance.pk)

def get_full_item_url(collection_name, instance):
    return u'{}{}/{}/{}/'.format(django_settings.SITE_URL, collection_name, instance.pk, tourldash(unicode(instance)))

def get_http_item_url(collection_name, instance):
    url = get_full_item_url(collection_name, instance)
    if 'http' not in url:
        url = 'http:' + url
    return url

class ItemModel(models.Model):
    collection_name = ''

    @property
    def item_url(self):
        return get_item_url(self.collection_name, self)

    @property
    def ajax_item_url(self):
        return get_ajax_item_url(self.collection_name, self)

    @property
    def full_item_url(self):
        return get_full_item_url(self.collection_name, self)

    @property
    def http_item_url(self):
        return get_http_item_url(self.collection_name, self)

    @property
    def image_url(self):
        if not hasattr(self, 'image'):
            return None
        return get_image_url(self.image)

    @property
    def http_image_url(self):
        if not hasattr(self, 'image'):
            return None
        return get_http_image_url(self.image)

    class Meta:
        abstract = True
