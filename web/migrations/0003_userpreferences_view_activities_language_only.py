# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0002_auto_20160807_1332'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='view_activities_language_only',
            field=models.BooleanField(default=True, verbose_name='View activities in your language only?'),
            preserve_default=True,
        ),
    ]
