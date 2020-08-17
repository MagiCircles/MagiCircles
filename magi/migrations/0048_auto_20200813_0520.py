# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0047_auto_20200307_0759'),
    ]

    operations = [
        migrations.AddField(
            model_name='userimage',
            name='_thumbnail_image',
            field=models.ImageField(null=True, upload_to=magi.utils.uploadThumb(b'user_images')),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='i_type',
            field=models.CharField(max_length=20, verbose_name='Platform'),
            preserve_default=True,
        ),
    ]
