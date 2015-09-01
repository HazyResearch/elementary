# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Regexp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('regexp', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('creator', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('repo', models.ForeignKey(related_name='regexps', to='resources.Repository')),
            ],
        ),
        migrations.RemoveField(
            model_name='result',
            name='doc',
        ),
        migrations.RemoveField(
            model_name='result',
            name='repo',
        ),
        migrations.DeleteModel(
            name='Result',
        ),
        migrations.AlterUniqueTogether(
            name='regexp',
            unique_together=set([('repo', 'creator', 'name')]),
        ),
    ]
