# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0043_auto_20190314_1527'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_j_tabs_with_content',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='_original_image',
            field=models.ImageField(null=True, upload_to=magi.utils.uploadTiny(b'activities')),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='image',
            field=models.ImageField(help_text='Only post official artworks, artworks you own, or fan artworks that are approved by the artist and credited.', upload_to=magi.utils.uploadToRandom(b'activities'), null=True, verbose_name='Image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='image',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'badges'), verbose_name='Image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='donationmonth',
            name='image',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'badges'), verbose_name='Image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='image',
            field=models.ImageField(max_length=1200, null=True, upload_to=magi.utils.uploadItem(b'notifications'), blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), verbose_name=b'Prize image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image2',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'2nd image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image3',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'3rd image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image4',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'4th image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='staffdetails',
            name='image',
            field=models.ImageField(help_text=b"Photograph of yourself. Real life photos look friendlier when we introduce the team. If you really don't want to show your face, you can use an avatar, but we prefer photos :)", upload_to=magi.utils.uploadToRandom(b'staff_photos'), null=True, verbose_name='Image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userimage',
            name='image',
            field=models.ImageField(upload_to=magi.utils.uploadToRandom(b'user_images')),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='i_type',
            field=models.CharField(max_length=20, verbose_name='Platform', choices=[(b'twitter', b'Twitter'), (b'facebook', b'Facebook'), (b'reddit', b'Reddit'), (b'bang', b'Bandori Party'), (b'starlight', b'Starlight Academy'), (b'cpro', b'Cinderella Producers'), (b'schoolidolu', b'School Idol Tomodachi'), (b'stardustrun', b'Stardust Run'), (b'frgl', b'fr.gl'), (b'instagram', b'Instagram'), (b'youtube', b'YouTube'), (b'tumblr', b'Tumblr'), (b'twitch', b'Twitch'), (b'steam', b'Steam'), (b'osu', b'osu!'), (b'pixiv', b'Pixiv'), (b'deviantart', b'DeviantArt'), (b'crunchyroll', b'Crunchyroll'), (b'mal', b'MyAnimeList'), (b'animeplanet', b'Anime-Planet'), (b'myfigurecollection', b'MyFigureCollection'), (b'line', b'LINE Messenger'), (b'github', b'GitHub'), (b'carrd', b'Carrd'), (b'listography', b'Listography')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='value',
            field=models.CharField(help_text='Write your username only, no URL.', max_length=64, verbose_name='Username/ID', validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z\\-_\\. /]*$', b'Only alphanumeric and - _ characters are allowed.')]),
            preserve_default=True,
        ),
    ]
