# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0016_auto_20161101_1850'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpreferences',
            name='language',
            field=models.CharField(max_length=10, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian'), (b'fr', 'French'), (b'de', 'German'), (b'pl', 'Polish'), (b'ja', 'Japanese'), (b'kr', 'Korean'), (b'zh-hans', 'Simplified Chinese'), (b'pt-br', 'Brazilian Portuguese')]),
            preserve_default=True,
        ),
    ]
