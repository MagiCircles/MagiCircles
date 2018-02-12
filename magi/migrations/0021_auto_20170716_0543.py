# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0020_auto_20170708_1635'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activity',
            old_name='tags_string',
            new_name='c_tags',
        ),
        migrations.RenameField(
            model_name='activity',
            old_name='language',
            new_name='i_language',
        ),
        migrations.RenameField(
            model_name='userpreferences',
            old_name='language',
            new_name='i_language',
        ),
    ]
