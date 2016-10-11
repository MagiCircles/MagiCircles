# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.conf import settings
import web.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('web', '0013_auto_20161001_0532'),
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(default=datetime.datetime.now)),
                ('name', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=300)),
                ('image', models.ImageField(upload_to=web.models.uploadToRandom(b'badges/'), verbose_name='Image')),
                ('url', models.CharField(max_length=200, null=True)),
                ('show_on_top_profile', models.BooleanField(default=False, help_text=b'Will be displayed near the share buttons on top of the profile. Generally reserved for donation badges.')),
                ('show_on_profile', models.BooleanField(default=False, help_text=b'Will be displayed in the "Badges" tab of the profile. Generally only unchecked for donations under $10.')),
                ('rank', models.PositiveIntegerField(blank=True, help_text=b'Top 3 of this specific badge. Generally used for donators badges', null=True, choices=[(1, 'Bronze'), (2, 'Silver'), (3, 'Gold')])),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DonationMonth',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(default=datetime.datetime.now)),
                ('cost', models.FloatField(default=250)),
                ('donations', models.FloatField(default=0)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='badge',
            name='donation_month',
            field=models.ForeignKey(related_name='badges', to='web.DonationMonth', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='badge',
            name='owner',
            field=models.ForeignKey(related_name='badges_created', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='badge',
            name='user',
            field=models.ForeignKey(related_name='badges', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='_cache_owner_preferences_status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Player'), (b'LOVER', 'Super Player'), (b'AMBASSADOR', 'Extreme Player'), (b'PRODUCER', 'Master Player'), (b'DEVOTEE', 'Ultimate Player')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='relevance',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='How often do you tweet/stream/post about ?', choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='status',
            field=models.CharField(max_length=12, null=True, choices=[(b'THANKS', b'Thanks'), (b'SUPPORTER', 'Player'), (b'LOVER', 'Super Player'), (b'AMBASSADOR', 'Extreme Player'), (b'PRODUCER', 'Master Player'), (b'DEVOTEE', 'Ultimate Player')]),
            preserve_default=True,
        ),
    ]
