from web.utils import tourldash
from web import models
from web.settings import SITE_URL

############################################################
# Get total donators

def totalDonators():
    return models.UserPreferences.objects.filter(status__isnull=False).exclude(status__exact='').count()
