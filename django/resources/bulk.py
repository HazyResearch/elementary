import logging
from elasticsearch import Elasticsearch
from pymongo import MongoClient
from .models import Document

es = Elasticsearch()

def elastic_delete_repo(repo):
    INDEX_NAME = 'elem'
    es.delete_by_query(index = INDEX_NAME, doc_type = 'docs', q = 'repo:' + repo)
  

def elastic_delete_docids(repo, docids):
    bulk_data = []
    INDEX_NAME = 'elem'
    for id in doc_ids:
        op_dict = {
            "delete": {
                "_index": INDEX_NAME,
                "_type": 'docs',
                "_id": id
            }
        }
        bulk_data.append(op_dict)
    res = es.bulk(index = INDEX_NAME, body = bulk_data, refresh = True)

def elastic_add_or_replace(repo, docs):
    bulk_data = []
    INDEX_NAME = 'elem'
    N=10000
    TIMEOUT=300
    for d in docs:
        id = d['_id']
        content = d['content']

        op_dict = {
            "index": {
                "_index": INDEX_NAME,
                "_type": 'docs',
                "_id": id
            }
        }
        data_dict = {
            'id': id,
            'doc_url': d.get('doc_url', ''),
            'created': d.get('created'),
            'content': content,
            'repo': repo.name,
            'processing': d.get('processing'),
            'result': d.get('result', {}),
            'markup_partners' : d.get('markup_partners', {}),
            'regexp_partners' : d.get('regexp_partners', {})
        }
        bulk_data.append(op_dict)
        bulk_data.append(data_dict)
        if len(bulk_data) > 1000:
           res = es.bulk(index = INDEX_NAME, body = bulk_data, refresh = True, timeout=TIMEOUT)
           bulk_data = []

    if len(bulk_data) > 0:
       res = es.bulk(index = INDEX_NAME, body = bulk_data, refresh = True, timeout=TIMEOUT)




def mongo_delete_repo(repo):
    collection = Document.get_mongo_collection()
    collection.remove({'repo':repo})
    collection.database.client.close()
