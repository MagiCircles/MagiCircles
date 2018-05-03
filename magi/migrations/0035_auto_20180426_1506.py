# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0034_auto_20180425_0348'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activity',
            old_name='message',
            new_name='m_message',
        ),
        migrations.AddField(
            model_name='activity',
            name='_cache_message',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
