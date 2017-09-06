# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.models


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0003_userpreferences_view_activities_language_only'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='image',
            field=models.ImageField(upload_to=magi.models.uploadToRandom(b'activities/'), null=True, verbose_name='Image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='image',
            field=models.ImageField(null=True, upload_to=magi.models.uploadToRandom(b'notifications/'), blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userimage',
            name='image',
            field=models.ImageField(upload_to=magi.models.uploadToRandom(b'user_images/')),
            preserve_default=True,
        ),
    ]
