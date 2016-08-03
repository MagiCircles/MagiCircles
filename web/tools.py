from web import models

############################################################
# Get total donators

def totalDonators():
    return models.UserPreferences.objects.filter(status__isnull=False).exclude(status__exact='').count()
