# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('test', '0003_book_chapter_paragraph'),
    ]

    operations = [
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('_cache_idol_last_update', models.DateTimeField(null=True)),
                ('_cache_j_idol', models.TextField(null=True)),
                ('_cache_gachas_last_update', models.DateTimeField(null=True)),
                ('_cache_j_gachas', models.TextField(null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Gacha',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('image', models.ImageField(upload_to=magi.utils.uploadItem(b'gacha'))),
                ('card', models.ForeignKey(related_name='gachas', to='test.Card', null=True)),
                ('owner', models.ForeignKey(related_name='added_gachas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Idol',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('japanese_name', models.CharField(max_length=100, null=True)),
                ('image', models.ImageField(upload_to=magi.utils.uploadItem(b'idols'))),
                ('owner', models.ForeignKey(related_name='added_idols', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='card',
            name='idol',
            field=models.ForeignKey(related_name='cards', to='test.Idol', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='card',
            name='owner',
            field=models.ForeignKey(related_name='added_cards', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
