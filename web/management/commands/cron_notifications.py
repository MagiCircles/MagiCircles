# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _, string_concat, activate as translation_activate
from web import models
from web.settings import SITE_NAME
from web.utils import send_email, emailContext
from web.urls import * # unused, just to make sure raw_context is updated
from pprint import pprint

class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):

        sent = []
        notifications = models.Notification.objects.filter(email_sent=False).select_related('owner', 'owner__preferences')
        for notification in notifications:
            preferences = notification.owner.preferences
            if preferences.is_notification_email_allowed(notification.message):
                notification_sent = notification.owner.email + notification.english_message + notification.website_url
                if notification_sent in sent:
                    print u' Duplicate not sent to {}: {}'.format(notification.owner.username, notification.english_message)
                else:
                    translation_activate(preferences.language if preferences.language else 'en')
                    context = emailContext()
                    context['notification'] = notification
                    context['user'] = notification.owner
                    try:
                        send_email(
                            subject=u'{} {}: {}'.format(SITE_NAME, unicode(_('Notification')), notification.localized_message),
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
                        notification.owner.preferences.invalid_email = True
                        notification.owner.preferences.save()
            else:
                try:
                    print '  No email for {}: {}'.format(notification.owner.username, notification.localized_message.replace('\n', ''))
                except:
                    print 'No email'
            notification.email_sent = True
            notification.save()
