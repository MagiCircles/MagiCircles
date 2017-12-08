# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('magi', '0024_auto_20170812_1004'),
    ]

    operations = [
        migrations.AddField(
            model_name='donationmonth',
            name='owner',
            field=models.ForeignKey(related_name='donation_month_created', default=1, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
