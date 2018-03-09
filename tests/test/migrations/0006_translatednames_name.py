# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test', '0005_translatednames'),
    ]

    operations = [
        migrations.AddField(
            model_name='translatednames',
            name='name',
            field=models.CharField(default='Maria', max_length=100),
            preserve_default=False,
        ),
    ]
