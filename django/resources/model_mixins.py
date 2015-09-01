from django.conf import settings
from django.db import models
from pymongo import MongoClient
from elasticsearch import Elasticsearch

# placeholder for refreshing elasticsearch when documents
# are updated. currently, documents are inserted into elasticsearch when
# dd pipeline is run.

class ElasticMixin(models.Model):

    def create_elastic_data(self, data):
        es = self.get_elastic()
        es.index(index=settings.ELASTIC_INDEX_NAME, doc_type='docs', id=self.docid,
                body=data)

    def update_elastic_data(self, data):
        es = self.get_elastic()
        es.update(index=settings.ELASTIC_INDEX_NAME, doc_type='docs', id=self.docid,
                body=data)

    def delete_elastic_data(self):
        es = self.get_elastic()
        es.delete(index=ELASTIC_INDEX_NAME, doc_type='docs', id=self.docid)

    @classmethod
    def _get_elastic(cls):
        if hasattr(cls, '_es'):
            es = cls._es
        else:
            es = Elasticsearch()
            cls._es = es
        return es

    def get_elastic(self):
        return self.__class__._get_elastic()

    class Meta:
        abstract = True


class MongoMixin(models.Model):

    @property
    def mongo_data(self):
        if not self.id:
            return None
        if hasattr(self, '_mongo_data_cache'):
            return self._mongo_data_cache
        data = self._exec_mongo_request('find_one')
        self._mongo_data_cache = data
        return data

    #def update_mongo_data(self, data):
    #    self._exec_mongo_request('update_one', [{'$set': data}, True])  # True: upsert

    def update_mongo_data(self, data):
        self._exec_mongo_request('update_one', [data, True])  # True: upsert

    def delete_mongo_data(self):
        self._exec_mongo_request('delete_one')

    @classmethod
    def get_mongo_collection(cls):
        client = MongoClient(**settings.MONGODB_CONNECTION_PARAMS)
        db = client[settings.MONGO_DB_NAME]
        model_name = cls.__name__
        collection = db[model_name]
        return collection

    def _exec_mongo_request(self, command, args=None):
        if hasattr(self.__class__, '_mongo_collection'):
            collection = self.__class__._mongo_collection
        else:
            collection = self.__class__.get_mongo_collection()
            self.__class__._mongo_collection = collection
        if command not in ['find_one', 'update_one', 'delete_one']:
            raise ValueError('Bad command: %s' % command)
        if not self.pk:
            raise ValueError('No PK value found. Has the object been saved?')
        spec = {'_id': self.pk}
        func = getattr(collection, command)
        # if there is a connection failure, this operation would fail,
        # but pymongo would reconnect in the background -- hopefully in time for next operation.
        if not args:
            args = []
        return func(spec, *args)

    class Meta:
        abstract = True
