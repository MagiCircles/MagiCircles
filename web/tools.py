from web.utils import tourldash
from web import models
from web.settings import SITE_URL

############################################################
# Get total donators

def totalDonators():
    return models.UserPreferences.objects.filter(status__isnull=False).exclude(status__exact='').count()

############################################################
# Full Item URL

def itemURL(name, item, ajax=False):
    if ajax:
        return u'/ajax/{}/{}/'.format(name, item.pk)
    return u'/{}/{}/{}/'.format(name, item.pk, tourldash(unicode(item)))

def fullItemURL(name, item):
    return u'{}{}/{}/{}/'.format(SITE_URL, name, item.pk, tourldash(unicode(item)))
