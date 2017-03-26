from web.utils import tourldash
from web import models
from web.settings import SITE_URL

############################################################
# Get total donators

def totalDonators():
    return models.UserPreferences.objects.filter(i_status__isnull=False).exclude(i_status__exact='').count()
