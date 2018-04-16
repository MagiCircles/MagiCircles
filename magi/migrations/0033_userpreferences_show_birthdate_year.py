# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0032_staffdetails'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='show_birthdate_year',
            field=models.BooleanField(default=True, verbose_name='Display your birthdate year'),
            preserve_default=True,
        ),
    ]
