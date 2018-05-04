# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0035_auto_20180426_1506'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='j_settings_per_groups',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
