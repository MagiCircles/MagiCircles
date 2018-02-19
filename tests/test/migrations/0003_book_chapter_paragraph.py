# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('test', '0002_ichoicestest_i_play_with'),
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('_cache_owner_last_update', models.DateTimeField(null=True)),
                ('_cache_owner_username', models.CharField(max_length=32, null=True)),
                ('_cache_owner_email', models.EmailField(max_length=75, blank=True)),
                ('_cache_owner_preferences_i_status', models.CharField(max_length=12, null=True)),
                ('_cache_owner_preferences_twitter', models.CharField(max_length=32, null=True, blank=True)),
                ('_cache_owner_color', models.CharField(max_length=100, null=True, blank=True)),
                ('owner', models.ForeignKey(related_name='books', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('_cache_owner_last_update', models.DateTimeField(null=True)),
                ('_cache_owner_username', models.CharField(max_length=32, null=True)),
                ('_cache_owner_email', models.EmailField(max_length=75, blank=True)),
                ('_cache_owner_preferences_i_status', models.CharField(max_length=12, null=True)),
                ('_cache_owner_preferences_twitter', models.CharField(max_length=32, null=True, blank=True)),
                ('_cache_owner_color', models.CharField(max_length=100, null=True, blank=True)),
                ('book', models.ForeignKey(related_name='chapters', to='test.Book')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Paragraph',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('_cache_owner_last_update', models.DateTimeField(null=True)),
                ('_cache_owner_username', models.CharField(max_length=32, null=True)),
                ('_cache_owner_email', models.EmailField(max_length=75, blank=True)),
                ('_cache_owner_preferences_i_status', models.CharField(max_length=12, null=True)),
                ('_cache_owner_preferences_twitter', models.CharField(max_length=32, null=True, blank=True)),
                ('_cache_owner_color', models.CharField(max_length=100, null=True, blank=True)),
                ('chapter', models.ForeignKey(related_name='paragraphs', to='test.Chapter')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
