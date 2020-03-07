# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0045_auto_20200228_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userlink',
            name='i_type',
            field=models.CharField(max_length=20, verbose_name='Platform', choices=[(b'twitter', b'Twitter'), (b'facebook', b'Facebook'), (b'reddit', b'Reddit'), (b'idolstory', b'Idol Story'), (b'starlight', b'Starlight Academy'), (b'cpro', b'Cinderella Producers'), (b'schoolidolu', b'School Idol Tomodachi'), (b'stardustrun', b'Stardust Run'), (b'frgl', b'fr.gl'), (b'instagram', b'Instagram'), (b'youtube', b'YouTube'), (b'tumblr', b'Tumblr'), (b'twitch', b'Twitch'), (b'steam', b'Steam'), (b'osu', b'osu!'), (b'pixiv', b'Pixiv'), (b'deviantart', b'DeviantArt'), (b'crunchyroll', b'Crunchyroll'), (b'mal', b'MyAnimeList'), (b'animeplanet', b'Anime-Planet'), (b'myfigurecollection', b'MyFigureCollection'), (b'line', b'LINE Messenger'), (b'github', b'GitHub'), (b'carrd', b'Carrd'), (b'listography', b'Listography')]),
            preserve_default=True,
        ),
    ]
