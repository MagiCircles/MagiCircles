# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0042_auto_20180930_1115'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userpreferences',
            old_name='unread_notifications',
            new_name='_cache_unread_notifications',
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_reputation',
            field=models.IntegerField(null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_reputation_last_update',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_unread_notifications_last_update',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='description',
            field=models.CharField(max_length=300, verbose_name='Description'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='badge',
            name='name',
            field=models.CharField(max_length=50, null=True, verbose_name='Title'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='report',
            name='staff_message',
            field=models.TextField(null=True, verbose_name=b'Staff message'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='staffdetails',
            name='d_favorite_foods',
            field=models.TextField(null=True, verbose_name='Liked food'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='favorite_character1',
            field=models.CharField(max_length=200, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='favorite_character2',
            field=models.CharField(max_length=200, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='favorite_character3',
            field=models.CharField(max_length=200, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='i_activities_language',
            field=models.CharField(max_length=10, verbose_name='Always post activities in {language}'),
            preserve_default=True,
        ),
    ]
