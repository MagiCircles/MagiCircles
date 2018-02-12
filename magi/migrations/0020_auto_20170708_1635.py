# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0019_auto_20170328_2309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'fr', 'French'), (b'de', 'German'), (b'it', 'Italian'), (b'ru', 'Russian')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='i_relevance',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='How often do you tweet/stream/post about Sample Game?', choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='language',
            field=models.CharField(max_length=10, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'fr', 'French'), (b'de', 'German'), (b'it', 'Italian'), (b'ru', 'Russian')]),
            preserve_default=True,
        ),
    ]
