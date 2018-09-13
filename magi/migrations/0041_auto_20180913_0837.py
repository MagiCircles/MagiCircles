# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0040_auto_20180912_0940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='image',
            field=models.ImageField(max_length=1200, null=True, upload_to=magi.utils.uploadItem(b'notifications/'), blank=True),
            preserve_default=True,
        ),
    ]
