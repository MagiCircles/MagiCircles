# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0030_auto_20180227_0803'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='c_groups',
            field=models.TextField(null=True, verbose_name='Roles', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='d_extra',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
