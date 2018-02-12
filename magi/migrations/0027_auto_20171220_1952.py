# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0026_auto_20171220_1709'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='_cache_owner_preferences_i_status',
            field=models.CharField(max_length=12, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='i_status',
            field=models.CharField(max_length=12, null=True, verbose_name='Status'),
            preserve_default=True,
        ),
    ]
