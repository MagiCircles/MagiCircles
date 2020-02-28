# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import magi.utils


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0044_auto_20191021_0926'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activity',
            options={'ordering': ['-last_bump'], 'verbose_name_plural': 'activities'},
        ),
        migrations.AlterModelOptions(
            name='badge',
            options={'ordering': ['-date']},
        ),
        migrations.AlterModelOptions(
            name='donationmonth',
            options={'ordering': ['-date']},
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={'ordering': ['-creation', '-id']},
        ),
        migrations.AlterModelOptions(
            name='report',
            options={'ordering': ['i_status']},
        ),
        migrations.AlterModelOptions(
            name='staffconfiguration',
            options={'ordering': ['id']},
        ),
        migrations.AlterField(
            model_name='activity',
            name='m_message',
            field=models.TextField(null=True, verbose_name='Message'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image2',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'2nd image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image3',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'3rd image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='prize',
            name='image4',
            field=models.ImageField(upload_to=magi.utils.uploadItem(b'prize'), null=True, verbose_name=b'4th image', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='staffdetails',
            name='image',
            field=models.ImageField(help_text=b"Photograph of yourself. Real life photos look friendlier when we introduce the team. If you really don't want to show your face, you can use an avatar, but we prefer photos :)", upload_to=magi.utils.uploadToRandom(b'staff_photos'), null=True, verbose_name='Image', blank=True),
            preserve_default=True,
        ),
    ]
