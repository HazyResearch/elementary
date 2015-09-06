from functools import wraps

from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Document, DocSource, Regexp, Repository
from .tasks import process_docs_queue, ingest_sources_queue

import uuid

def catch_dml_failure(message='Update failed because it violates DB integrity'):
    def wrapper(f):
        @wraps(f)
        def wrapped(self, *f_args, **f_kwargs):
            try:
                return f(self, *f_args, **f_kwargs)
            except IntegrityError as ie:
                raise ValidationError(message)
        return wrapped
    return wrapper

class UserSerializer(serializers.ModelSerializer):
    username = serializers.RegexField(r'\w+')
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    url = serializers.HyperlinkedIdentityField(
        view_name='user-detail',
        lookup_field='username'
    )

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'password')

    @catch_dml_failure('User name already exists')
    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    @catch_dml_failure('User name already exists')
    def update(self, instance, validated_data):
        password = validated_data.pop('password')
        super(UserSerializer, self).update(instance, validated_data)
        instance.set_password(password)
        instance.save()
        return instance


class RepositorySerializer(serializers.ModelSerializer):
    #owner = serializers.ReadOnlyField(source='owner.username')
    name = serializers.RegexField(r'\w+')
    pipeline = serializers.ChoiceField(Repository.PIPELINE_CHOICES, allow_blank=True)
    url = serializers.HyperlinkedIdentityField(
        view_name='repository-detail',
        lookup_field='name' #'full_name'
    )
    docs = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = ('url', 'docs', 'sources', #'owner', 
             'name', 'pipeline', 'created')

    def get_docs(self, obj):
        url = '/docs/%s/' % obj.name #full_name
        return self.context['request'].build_absolute_uri(url)

    def get_sources(self, obj):
        url = '/sources/%s/' % obj.name #full_name
        return self.context['request'].build_absolute_uri(url)

    #@catch_dml_failure('Repo name already exists')
    def create(self, validated_data):
        return super(RepositorySerializer, self).create(validated_data)

    @catch_dml_failure('Repo name already exists')
    def update(self, instance, validated_data):
        return super(RepositorySerializer, self).update(instance, validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    #repo = serializers.StringRelatedField(source='repo.full_name')
    repo = serializers.StringRelatedField(source='repo.name')
    docid = serializers.CharField(max_length=100, trim_whitespace=True)
    doc_url = serializers.URLField(max_length=1000, allow_blank=True, source='url')
    content = serializers.CharField(trim_whitespace=True)
    created = serializers.ReadOnlyField()
    #processed = serializers.ReadOnlyField()
    url = serializers.SerializerMethodField()
    #processing = serializers.SerializerMethodField()
    #result = serializers.SerializerMethodField()
    processing = serializers.ReadOnlyField()
    markup_partners = serializers.ReadOnlyField()
    regexp_partners = serializers.ReadOnlyField()

    class Meta:
        model = Document
        fields = ('url', 'repo', 'docid', 'doc_url', 'created', #'processed', 
           'content', 'processing', 'result', 'markup_partners', 'regexp_partners')

    def get_url(self, obj):
        url = '/docs/%s/' % obj.full_name
        return self.context['request'].build_absolute_uri(url)

    def get_processing(self, obj):
	if obj.is_preprocessed:
	    return {'_status': 'PREPROCESSED'}
	if not obj.processed:
            return {'_status': 'NOT_PROCESSED_YET'}
        if obj.processed and not obj.result:
            if obj.processing_error:
                return {
                    '_status': 'ERROR',
                    '_error': obj.processing_error
                }
            return {'_status': 'NO_EXTRACTIONS'}
	return {'_status': 'PROCESSED'} 

    #def get_result(self, obj):
    #	return obj.result
	#if obj.is_preprocessed:
	    
        #if not obj.processed:
        #    return {'_status': 'NOT_PROCESSED_YET'}
        #if obj.processed and not obj.result:
        #    if obj.processing_error:
        #        return {
        #            '_status': 'ERROR',
        #            '_error': obj.processing_error
        #        }
        #    return {'_status': 'NO_EXTRACTIONS'}
        #return obj.result

    @catch_dml_failure('Value of docid conflicts with existing records')
    def create(self, validated_data):
        instance = super(DocumentSerializer, self).create(validated_data)
        obj = {
            'docid': instance.docid,
            'url': self.get_url(instance),
            'repo': instance.repo.name,
            'content': validated_data['content'],
            'created': instance.created,
            'processing':{ '_status': 'NOT_PROCESSED_YET' },
            'result': {},
            'markup_partners': {},
            'regexp_partners': {}
        }
        instance.update_mongo_data({ '$set' : obj })
        instance.create_elastic_data(obj)
        process_docs_queue.fill()
        return instance

    @catch_dml_failure('Value of docid conflicts with existing records')
    def update(self, instance, validated_data):
        content = validated_data.pop('content')
        super(DocumentSerializer, self).update(instance, validated_data)
        if instance.content != content:
            instance.update_mongo_data({ '$set' : {
                'content': content
            }})
            instance.update_elastic_data({
                'content': content
            })
        return instance

    def delete(self, instance):
        super(DocumentSerializer, self).delete(instance)
        instance.delete_mongo_data()
        instance.delete_elastic_data()

def random_uuid_hex():
    return uuid.uuid4().hex

class DocSourceSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    crawlid = serializers.CharField(trim_whitespace=True, default=random_uuid_hex)
    #repo = serializers.StringRelatedField(source='repo.full_name')
    repo = serializers.StringRelatedField(source='repo.name')
    source_url = serializers.URLField(max_length=1000, allow_blank=True, source='url')
    #creator = serializers.StringRelatedField(source='creator.username')
    created = serializers.ReadOnlyField()
    processed = serializers.ReadOnlyField()
    total_docs = serializers.ReadOnlyField()
    ingested_docs = serializers.ReadOnlyField()
    invalid_docs = serializers.ReadOnlyField()
    processed_docs = serializers.ReadOnlyField()
    ingestion_log = serializers.ReadOnlyField()

    class Meta:
        model = DocSource
        fields = ('url', 'crawlid', 'repo', 'source_url', #'creator', 
            'created',
            'processed', 'total_docs', 'ingested_docs', 'invalid_docs', 'processed_docs', 'ingestion_log')

    def get_url(self, obj):
        #url = '/sources/%s/%s/' % (obj.repo.full_name, obj.pk)
        url = '/sources/%s/%s/' % (obj.repo.name, obj.pk)
        return self.context['request'].build_absolute_uri(url)

    @catch_dml_failure('Value of crawlid conflicts with existing records')
    def create(self, validated_data):
        instance = super(DocSourceSerializer, self).create(validated_data)
        ingest_sources_queue.fill()
        return instance

class RegexpSerializer(serializers.ModelSerializer):
    name = serializers.RegexField(r'\w+')
    repo = serializers.StringRelatedField(source='repo.name')
    regexp = serializers.CharField(trim_whitespace=True)
    owner = serializers.StringRelatedField(source='owner.username')
    created = serializers.ReadOnlyField()

    class Meta:
        model = Regexp
        fields = ('name', 'repo', 'regexp', 'owner', 'created')

    #def get_url(self, obj):
    #    #url = '/sources/%s/%s/' % (obj.repo.full_name, obj.pk)
    #    url = '/regexps/%s/%s/' % (obj.repo.name, obj.pk)
    #    return self.context['request'].build_absolute_uri(url)

    #@catch_dml_failure('Value of name conflicts with existing records')
    def create(self, validated_data):
        instance = super(RegexpSerializer, self).create(validated_data)
        return instance

