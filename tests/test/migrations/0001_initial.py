# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation', models.DateTimeField(auto_now_add=True)),
                ('level', models.PositiveIntegerField(null=True, verbose_name='Level')),
                ('owner', models.ForeignKey(related_name='accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CCSVTest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('c_data', models.TextField(null=True, blank=True)),
                ('c_abilities', models.TextField(null=True, blank=True)),
                ('c_tags', models.TextField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IChoicesTest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('i_attribute', models.PositiveIntegerField(default=0, choices=[(0, b'smile'), (1, b'pure'), (2, b'cool')])),
                ('i_power', models.PositiveIntegerField(default=0, choices=[(0, 'Happy'), (1, 'Cool'), (2, 'Rock')])),
                ('i_super_power', models.PositiveIntegerField(default=0, choices=[(0, 'Happy'), (1, 'Cool'), (2, 'Rock')])),
                ('i_rarity', models.PositiveIntegerField(default=0, choices=[(0, b'N'), (1, b'R'), (2, b'SR')])),
                ('i_language', models.CharField(default=b'en', max_length=10, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish'), (b'ru', 'Russian'), (b'it', 'Italian')])),
                ('i_notification', models.PositiveIntegerField(default=0, verbose_name='Notification type', choices=[(0, 'When someone likes your activity.'), (1, 'When someone follows you.')])),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
