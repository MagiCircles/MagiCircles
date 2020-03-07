# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0046_auto_20200304_1713'),
    ]

    operations = [
        migrations.RenameField(
            model_name='badge',
            old_name='description',
            new_name='m_description',
        ),
        migrations.AlterField(
            model_name='badge',
            name='m_description',
            field=models.TextField(null=True, verbose_name='Description'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='badge',
            name='_cache_description',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
