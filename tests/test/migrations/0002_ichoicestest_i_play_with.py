# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('test', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ichoicestest',
            name='i_play_with',
            field=models.PositiveIntegerField(null=True, verbose_name='Play with', choices=[(0, 'Thumbs'), (1, 'All fingers'), (2, 'Index fingers'), (3, 'One hand'), (4, 'Other')]),
            preserve_default=True,
        ),
    ]
