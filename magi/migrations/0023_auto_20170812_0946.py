# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0022_auto_20170812_0431'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='message_data',
            new_name='c_message_data',
        ),
        migrations.AlterField(
            model_name='activity',
            name='i_language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'fr', 'French'), (b'de', 'German'), (b'it', 'Italian'), (b'ru', 'Russian')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='i_message',
            field=models.PositiveIntegerField(choices=[(0, 'When someone likes your activity.'), (1, 'When someone follows you.')]),
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
            name='i_language',
            field=models.CharField(max_length=10, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'fr', 'French'), (b'de', 'German'), (b'it', 'Italian'), (b'ru', 'Russian')]),
            preserve_default=True,
        ),
    ]
