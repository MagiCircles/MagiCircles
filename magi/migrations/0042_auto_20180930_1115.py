# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0041_auto_20180913_0837'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prize',
            name='i_character',
            field=models.CharField(max_length=200, null=True, verbose_name=b'Character'),
            preserve_default=True,
        ),
    ]
