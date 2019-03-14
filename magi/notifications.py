import datetime
from django.utils import timezone
from django.db.models import F
from magi.utils import join_data
from magi import models

def pushNotification(user, notification_type, values, url_values=None, image=None, force=False):
    """
    If a similar notification has been pushed less than 2 hours ago, it will not push a notification.
    Can be forced with force=True.
    """
    data = {
        'i_message': models.Notification.get_i('message', notification_type),
        'owner_id': user.id,
        'c_message_data': join_data(*values),
        'c_url_data': (join_data(*url_values) if url_values else None),
        'image': image,
    }

    if not force:
        now = timezone.now()
        two_hours_ago = now - datetime.timedelta(hours=2)
        previous_similar_notifications = models.Notification.objects.filter(
            creation__gt=two_hours_ago,
            seen=False,
        ).filter(**data)
        if previous_similar_notifications.count():
            return None

    notification = models.Notification.objects.create(**data)
    user.preferences.force_update_cache('unread_notifications')
    return notification
