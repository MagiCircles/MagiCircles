# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0049_auto_20211206_2357'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='is_suggestededit',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
    ]
