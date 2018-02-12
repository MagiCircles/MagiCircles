# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0021_auto_20170716_0543'),
    ]

    operations = [
        migrations.RenameField(
            model_name='notification',
            old_name='message',
            new_name='i_message',
        ),
        migrations.AlterField(
            model_name='activity',
            name='c_tags',
            field=models.TextField(null=True, verbose_name='Tags', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='i_language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian'), (b'fr', 'French'), (b'de', 'German'), (b'pl', 'Polish'), (b'ja', 'Japanese'), (b'kr', 'Korean'), (b'zh-hans', 'Simplified Chinese'), (b'pt-br', 'Brazilian Portuguese')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='i_relevance',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='How often do you tweet/stream/post about ?', choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='i_language',
            field=models.CharField(max_length=10, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian'), (b'fr', 'French'), (b'de', 'German'), (b'pl', 'Polish'), (b'ja', 'Japanese'), (b'kr', 'Korean'), (b'zh-hans', 'Simplified Chinese'), (b'pt-br', 'Brazilian Portuguese')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='i_status',
            field=models.CharField(max_length=12, null=True, verbose_name='Status', choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Player'), (b'LOVER', 'Super Player'), (b'AMBASSADOR', 'Extreme Player'), (b'PRODUCER', 'Master Player'), (b'DEVOTEE', 'Ultimate Player')]),
            preserve_default=True,
        ),
    ]
