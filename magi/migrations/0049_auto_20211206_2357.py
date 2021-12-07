# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0048_auto_20200813_0520'),
    ]

    operations = [
        migrations.AddField(
            model_name='userimage',
            name='name',
            field=models.CharField(max_length=100, null=True, verbose_name='Title'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='report',
            name='images',
            field=models.ManyToManyField(related_name='report', verbose_name='Images', to='magi.UserImage', blank=True),
            preserve_default=True,
        ),
    ]
