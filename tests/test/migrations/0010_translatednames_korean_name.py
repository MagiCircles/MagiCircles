# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test', '0009_idol_d_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='translatednames',
            name='korean_name',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
