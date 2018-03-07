# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test', '0004_auto_20180306_0959'),
    ]

    operations = [
        migrations.CreateModel(
            name='TranslatedNames',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('d_names', models.TextField(null=True)),
                ('d_colors', models.TextField(null=True)),
                ('d_items', models.TextField(null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
