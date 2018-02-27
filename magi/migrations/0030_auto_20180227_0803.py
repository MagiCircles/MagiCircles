# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0029_auto_20180226_1004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='i_language',
            field=models.CharField(max_length=10, verbose_name='Language'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='staffconfiguration',
            name='i_language',
            field=models.CharField(max_length=10, null=True, verbose_name='Language'),
            preserve_default=True,
        ),
    ]
