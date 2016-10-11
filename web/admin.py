from django.contrib import admin
from web import models

admin.site.register(models.UserPreferences)
admin.site.register(models.UserLink)
admin.site.register(models.Activity)
admin.site.register(models.Notification)
admin.site.register(models.Report)
admin.site.register(models.DonationMonth)
admin.site.register(models.Badge)
