# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0017_auto_20161101_1931'),
    ]

    operations = [
        migrations.RenameField(
            model_name='report',
            old_name='status',
            new_name='i_status',
        ),
        migrations.RenameField(
            model_name='userlink',
            old_name='type',
            new_name='i_type',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='_cache_owner_preferences_status',
        ),
        migrations.RemoveField(
            model_name='userlink',
            name='relevance',
        ),
        migrations.RemoveField(
            model_name='userpreferences',
            name='status',
        ),
        migrations.AddField(
            model_name='activity',
            name='_cache_owner_preferences_i_status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Skilled Producer'), (b'LOVER', 'Expert Producer'), (b'AMBASSADOR', 'Veteran Producer'), (b'PRODUCER', 'Ultimate Producer'), (b'DEVOTEE', 'Idol Master')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='donationmonth',
            name='image',
            field=models.ImageField(default='', upload_to=magi.utils.uploadItem(b'badges/'), verbose_name='Image'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='report',
            name='reason',
            field=models.TextField(default='', verbose_name='Reason'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userlink',
            name='i_relevance',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='How often do you tweet/stream/post about IDOLM@STER Cinderella Girls Starlight Stage?', choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='i_status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Skilled Producer'), (b'LOVER', 'Expert Producer'), (b'AMBASSADOR', 'Veteran Producer'), (b'PRODUCER', 'Ultimate Producer'), (b'DEVOTEE', 'Idol Master')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='image',
            field=models.ImageField(help_text='Only post official artworks, artworks you own, or fan artworks that are approved by the artist and credited.', upload_to=magi.utils.uploadToRandom(b'activities/'), null=True, verbose_name='Image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='image',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'badges/'), verbose_name='Image'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='name',
            field=models.CharField(max_length=50, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='rank',
            field=models.PositiveIntegerField(blank=True, help_text=b'Top 3 of this specific badge.', null=True, choices=[(1, 'Bronze'), (2, 'Silver'), (3, 'Gold')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='show_on_profile',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='show_on_top_profile',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='image',
            field=models.ImageField(null=True, upload_to=magi.utils.uploadItem(b'notifications/'), blank=True),
            preserve_default=True,
        ),
    ]
