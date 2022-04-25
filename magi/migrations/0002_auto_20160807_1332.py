# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='owner',
            field=models.ForeignKey(related_name='reports', to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
