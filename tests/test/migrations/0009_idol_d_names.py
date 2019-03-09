# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test', '0008_auto_20180425_0350'),
    ]

    operations = [
        migrations.AddField(
            model_name='idol',
            name='d_names',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
