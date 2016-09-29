# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0006_auto_20160918_1236'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='_cache_owner_preferences_status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Skilled Producer'), (b'LOVER', 'Expert Producer'), (b'AMBASSADOR', 'Veteran Producer'), (b'PRODUCER', 'Ultimate Producer'), (b'DEVOTEE', 'Idol Master')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'fr', 'French')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='relevance',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='How often do you tweet/stream/post about IDOLM@STER Cinderella Girls Starlight Stage?', choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'fr', 'French')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Skilled Producer'), (b'LOVER', 'Expert Producer'), (b'AMBASSADOR', 'Veteran Producer'), (b'PRODUCER', 'Ultimate Producer'), (b'DEVOTEE', 'Idol Master')]),
            preserve_default=True,
        ),
    ]
