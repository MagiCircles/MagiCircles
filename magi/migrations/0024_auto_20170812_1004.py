# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0023_auto_20170812_0946'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='url_data',
            new_name='c_url_data',
        ),
    ]
