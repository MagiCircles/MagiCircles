from django.db.models import F
from web.utils import join_data
from web import models

def pushNotification(user, notification_type, values, url_values=None, image=None):
    """
    If preferences is not specified, it will use the preferences in user
    """
    notification = models.Notification.objects.create(
        owner=user,
        message=notification_type,
        message_data=join_data(*values),
        url_data=(join_data(*url_values) if url_values else None),
        image=image)
    models.UserPreferences.objects.filter(pk=user.preferences.pk).update(unread_notifications=F('unread_notifications') + 1)
    return notification
