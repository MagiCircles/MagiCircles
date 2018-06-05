# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0036_userpreferences_j_settings_per_groups'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activity',
            old_name='modification',
            new_name='last_bump',
        ),
        migrations.AlterField(
            model_name='activity',
            name='last_bump',
            field=models.DateTimeField(db_index=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='_original_image',
            field=models.ImageField(null=True, upload_to=magi.utils.uploadTiny(b'activities/')),
            preserve_default=True,
        ),
    ]
