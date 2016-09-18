# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0004_auto_20160809_1833'),
    ]

    operations = [
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
            model_name='userlink',
            name='type',
            field=models.CharField(max_length=20, verbose_name='Platform', choices=[(b'facebook', b'Facebook'), (b'twitter', b'Twitter'), (b'reddit', b'Reddit'), (b'schoolidolu', b'School Idol Tomodachi'), (b'stardustrun', b'Stardust Run'), (b'frgl', b'fr.gl'), (b'line', b'LINE Messenger'), (b'tumblr', b'Tumblr'), (b'twitch', b'Twitch'), (b'steam', b'Steam'), (b'instagram', b'Instagram'), (b'youtube', b'YouTube'), (b'github', b'GitHub')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='language',
            field=models.CharField(max_length=4, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'fr', 'French')]),
            preserve_default=True,
        ),
    ]
