from django.db import models
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.utils.http import urlquote

from .model_mixins import ElasticMixin

import uuid

class Repository(models.Model):
    PIPELINE_CHOICES = (
        ('memex/atf', 'Memex ATF'),
        ('memex/escort', 'Memex Escort'),
        ('genomics', 'Genomics')
    )
    name = models.TextField(primary_key=True)
    #owner = models.ForeignKey('auth.User', related_name='repos')
    created = models.DateTimeField(auto_now_add=True)
    pipeline = models.TextField(choices=PIPELINE_CHOICES, null=True)

    #class Meta:
    #    unique_together = ('owner', 'name')

    #@property
    #def full_name(self):
    #    return '%s/%s' % (self.owner.username, self.name)

    def __unicode__(self):
        return self.name 


class Document(ElasticMixin, models.Model):
    docid = models.TextField()
    repo = models.ForeignKey('Repository', related_name='docs')
    source = models.ForeignKey('DocSource', null=True, related_name='docs')
    # URL of the doc, if any
    url = models.TextField(null=True)
    # domain, doc type, etc.; currrently unused
    properties = HStoreField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    # will be updated by the processor
    is_preprocessed = models.BooleanField(default=False)
    # used to skip processing
    processed = models.DateTimeField(null=True)
    processing_error = models.TextField(null=True)

    class Meta:
        unique_together = ('repo', 'docid')

    @property
    def content(self):
        edata = self.elastic_data
        if not edata:
            return None
        return edata.get('content')

    def section_text(self, section):
        edata = self.elastic_data
        if not edata:
            return None
        return edata.get(section, None)

    @property
    def full_name(self):
        return '%s/%s' % (self.repo.name, self.docid)

    @property
    def processing(self):
        edata = self.elastic_data
        if not edata:
            return None
        return edata.get('processing', None)

    @property
    def result(self):
        edata = self.elastic_data
        if not edata:
            return None
        return edata.get('result', None)

    @property
    def markup_partners(self):
        edata = self.elastic_data
        if not edata:
            return {}
        return edata.get('markup_partners', {})

    @property
    def regexp_partners(self):
        edata = self.elastic_data
        if not edata:
            return {}
        return edata.get('regexp_partners', {})

    def __unicode__(self):
        return self.full_name

def random_uuid_hex():
    return uuid.uuid4().hex

class DocSource(models.Model):
    repo = models.ForeignKey('Repository', related_name='sources')
    # A source is fully specified in a URL; could be a pre-signed S3 object URL.
    # Response must be either of
    # 1. a text file
    # 2. a zip of one text file
    # Each line of the text file must be a JSON object with keys
    # docid and content; and optionally keys like 'url' and others.
    url = models.URLField(max_length=1000)
    crawlid = models.TextField(default=random_uuid_hex) 
    #creator = models.ForeignKey('auth.User')
    created = models.DateTimeField(auto_now_add=True)
    # fields below will be updated by the ingestor
    processed = models.DateTimeField(null=True)
    total_docs = models.BigIntegerField(null=True)
    ingested_docs = models.BigIntegerField(null=True)
    invalid_docs = models.BigIntegerField(null=True)
    processed_docs = models.BigIntegerField(null=True)
    ingestion_log = models.TextField(null=True)

    class Meta:
        #unique_together = ('repo', 'url')
        unique_together = ('repo', 'crawlid')

    def __unicode__(self):
        #return '[%s][%s] %s' % (self.id, self.repo.full_name, self.url)
        #return '[%s][%s] %s' % (self.id, self.repo.full_name, self.crawlid)
        return '[%s][%s] %s' % (self.id, self.repo.name, self.crawlid)

class Regexp(models.Model):
    repo = models.ForeignKey('Repository', related_name='regexps')
    name = models.TextField()
    regexp = models.TextField() 
    #creator = models.ForeignKey('auth.User')
    owner = models.ForeignKey('auth.User')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('repo', 'name')

    def __unicode__(self):
        return '[%s][%s] %s' % (self.id, self.repo.name, self.name)


#class Result(models.Model):
#    doc = models.ForeignKey('Document', related_name='results')
#    # denormalized field
#    repo = models.ForeignKey('Repository', related_name='results')
#    # record type, to be populated from the DD app output;
#    # semantics is determined by the DD app.
#    record_type = models.TextField(null=True)
#    # each record is an opaque blob; could be a string or a JSON
#    data = models.TextField()
#
