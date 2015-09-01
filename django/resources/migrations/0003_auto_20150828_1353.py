# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_auto_20150828_1243'),
    ]

    operations = [
        migrations.RenameField(
            model_name='regexp',
            old_name='creator',
            new_name='owner',
        ),
        migrations.AlterUniqueTogether(
            name='regexp',
            unique_together=set([('repo', 'name')]),
        ),
    ]
