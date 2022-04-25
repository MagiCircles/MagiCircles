# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('magi', '0028_userpreferences_default_tab'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffConfiguration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=100)),
                ('verbose_key', models.CharField(max_length=100, verbose_name=b'Name')),
                ('value', models.TextField(null=True, verbose_name=b'Value')),
                ('i_language', models.CharField(max_length=4, null=True, verbose_name='Language')),
                ('is_long', models.BooleanField(default=False)),
                ('is_markdown', models.BooleanField(default=False)),
                ('is_boolean', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(related_name='added_configurations', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='staffconfiguration',
            unique_together=set([('key', 'i_language')]),
        ),
    ]
