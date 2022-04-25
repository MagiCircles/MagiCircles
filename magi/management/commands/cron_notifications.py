# -*- coding: utf-8 -*-
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _, string_concat, activate as translation_activate
from django.utils import timezone
from magi.urls import * # unused, just to make sure raw_context is updated
from magi import models
from magi.settings import SITE_NAME, SITE_NAME_PER_LANGUAGE
from magi.utils import send_email, emailContext
from pprint import pprint

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):

        sent = []
        notifications = models.Notification.objects.filter(email_sent=False, seen=False).select_related('owner', 'owner__preferences')
        for notification in notifications:
            preferences = notification.owner.preferences
            if preferences.is_notification_email_allowed(notification.message):
                try:
                    notification_sent = notification.owner.email + notification.english_message + notification.website_url
                except Exception, e:
                    print u'!! Error when parsing notification', notification.id, e
                    continue
                if notification_sent in sent:
                    print u' Duplicate not sent to {}: {}'.format(notification.owner.username, notification.english_message)
                else:
                    language = preferences.language if preferences.i_language else 'en'
                    translation_activate(language)
                    context = emailContext()
                    context['notification'] = notification
                    context['user'] = notification.owner
                    try:
                        send_email(
                            subject=u'{} {}: {}'.format(SITE_NAME_PER_LANGUAGE.get(language, SITE_NAME), str(_('Notification')), notification.localized_message),
                            template_name='notification',
                            to=[notification.owner.email],
                            context=context,
                        )
                        try:
                            print u'Email sent to {}: {}'.format(notification.owner.username, notification.localized_message.replace('\n', ''))
                        except:
                            print 'Email sent'
                        sent.append(notification_sent)
                    except Exception, e:
                        print u'!! Error when sending email to {} !!'.format(notification.owner.email)
                        print e
            else:
                try:
                    print '  No email for {}: {}'.format(notification.owner.username, notification.localized_message.replace('\n', ''))
                except:
                    print 'No email'
            notification.email_sent = True
            notification.save()

        now = timezone.now()
        six_months_ago = now - datetime.timedelta(days=30*6)
        get_old_notifications = lambda: models.Notification.objects.filter(seen=True, creation__lt=six_months_ago)
        print 'Delete old notifications:', get_old_notifications().count()
        while get_old_notifications().count() > 0:
            models.Notification.objects.filter(id__in=[n.id for n in get_old_notifications()[:100]]).delete()
