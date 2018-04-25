# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('magi', '0033_userpreferences_show_birthdate_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='_cache_hidden_by_default',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='_cache_total_likes',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_c_blocked_by_ids',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='_cache_c_blocked_ids',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='blocked',
            field=models.ManyToManyField(related_name='blocked_by', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userpreferences',
            name='d_hidden_tags',
            field=models.TextField(null=True, verbose_name='Hide tags'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='modification',
            field=models.DateTimeField(auto_now=True, db_index=True),
            preserve_default=True,
        ),
    ]
