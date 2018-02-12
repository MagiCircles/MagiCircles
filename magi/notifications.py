from django.db.models import F
from magi.utils import join_data
from magi import models

def pushNotification(user, notification_type, values, url_values=None, image=None):
    """
    If preferences is not specified, it will use the preferences in user
    """
    notification = models.Notification.objects.create(
        owner=user,
        i_message=models.Notification.get_i('message', notification_type),
        c_message_data=join_data(*values),
        c_url_data=(join_data(*url_values) if url_values else None),
        image=image)
    models.UserPreferences.objects.filter(pk=user.preferences.pk).update(unread_notifications=F('unread_notifications') + 1)
    return notification
