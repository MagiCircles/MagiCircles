# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magi', '0025_auto_20171104_0427'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='i_language',
            field=models.CharField(max_length=4, verbose_name='Language'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='i_message',
            field=models.PositiveIntegerField(verbose_name='Notification type', choices=[(0, 'When someone likes your activity.'), (1, 'When someone follows you.')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='report',
            name='i_status',
            field=models.PositiveIntegerField(default=0, verbose_name=b'Status', choices=[(0, b'Pending'), (1, b'Deleted'), (2, b'Edited'), (3, b'Ignored')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userlink',
            name='i_relevance',
            field=models.PositiveIntegerField(blank=True, null=True, choices=[(0, 'Never'), (1, 'Sometimes'), (2, 'Often'), (3, 'Every single day')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userpreferences',
            name='i_language',
            field=models.CharField(max_length=10, verbose_name='Language'),
            preserve_default=True,
        ),
    ]
