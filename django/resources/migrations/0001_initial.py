# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore
import resources.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DocSource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(max_length=1000)),
                ('crawlid', models.TextField(default=resources.models.random_uuid_hex)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('processed', models.DateTimeField(null=True)),
                ('total_docs', models.BigIntegerField(null=True)),
                ('ingested_docs', models.BigIntegerField(null=True)),
                ('invalid_docs', models.BigIntegerField(null=True)),
                ('processed_docs', models.BigIntegerField(null=True)),
                ('ingestion_log', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('docid', models.TextField()),
                ('url', models.TextField(null=True)),
                ('properties', django.contrib.postgres.fields.hstore.HStoreField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('is_preprocessed', models.BooleanField(default=False)),
                ('processed', models.DateTimeField(null=True)),
                ('processing_error', models.TextField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('name', models.TextField(serialize=False, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('pipeline', models.TextField(null=True, choices=[(b'memex/atf', b'Memex ATF'), (b'memex/escort', b'Memex Escort'), (b'genomics', b'Genomics')])),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('record_type', models.TextField(null=True)),
                ('data', models.TextField()),
                ('doc', models.ForeignKey(related_name='results', to='resources.Document')),
                ('repo', models.ForeignKey(related_name='results', to='resources.Repository')),
            ],
        ),
        migrations.AddField(
            model_name='document',
            name='repo',
            field=models.ForeignKey(related_name='docs', to='resources.Repository'),
        ),
        migrations.AddField(
            model_name='document',
            name='source',
            field=models.ForeignKey(related_name='docs', to='resources.DocSource', null=True),
        ),
        migrations.AddField(
            model_name='docsource',
            name='repo',
            field=models.ForeignKey(related_name='sources', to='resources.Repository'),
        ),
        migrations.AlterUniqueTogether(
            name='document',
            unique_together=set([('repo', 'docid')]),
        ),
        migrations.AlterUniqueTogether(
            name='docsource',
            unique_together=set([('repo', 'crawlid')]),
        ),
    ]
