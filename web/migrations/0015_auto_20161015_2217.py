# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0014_auto_20161011_1829'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian'), (b'fr', 'French'), (b'de', 'German'), (b'pl', 'Polish'), (b'ja', 'Japanese'), (b'zh-hans', 'Simplified Chinese'), (b'pt-br', 'Brazilian Portuguese')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian'), (b'fr', 'French'), (b'de', 'German'), (b'pl', 'Polish'), (b'ja', 'Japanese'), (b'zh-hans', 'Simplified Chinese'), (b'pt-br', 'Brazilian Portuguese')]),
            preserve_default=True,
        ),
    ]
