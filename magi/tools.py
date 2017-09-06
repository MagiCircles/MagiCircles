from magi.utils import tourldash
from magi import models
from magi.settings import SITE_URL

############################################################
# Get total donators

def totalDonators():
    return models.UserPreferences.objects.filter(i_status__isnull=False).exclude(i_status__exact='').count()
