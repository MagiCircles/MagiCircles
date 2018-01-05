# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0027_auto_20171220_1952'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='default_tab',
            field=models.CharField(max_length=100, null=True, verbose_name='Default tab'),
            preserve_default=True,
        ),
    ]
