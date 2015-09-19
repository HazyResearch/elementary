import logging
from elasticsearch import Elasticsearch
import sys

INDEX_NAME = 'elem'

es = Elasticsearch()

# repository crud

def create_repo(repo):
    body = {
        "_source" : { "enabled" : True },
        "properties" : {
            "content" : { "type" : "string", "index" : "analyzed" },
            "docid" : { "type" : "string", "index" : "not_analyzed" },
            "url" : { "type" : "string", "index" : "not_analyzed" },
            "ref" : { "type" : "string", "index" : "not_analyzed" }
        }
    }
    es.indices.put_mapping(index = INDEX_NAME, doc_type = repo, body = body)

def delete_repo(repo):
    es.indices.delete_mapping(index = INDEX_NAME, doc_type = repo)

# document crud

def create_doc(repo, docid, data):
    es.create(index = INDEX_NAME, doc_type = repo, id = docid, body = data)

def update_doc(repo, docid, data):
    es.update(index = INDEX_NAME, doc_type = repo, id = docid,
        body = data)

def delete_doc(repo, docid):
    es.delete(index = INDEX_NAME, doc_type = repo, id = docid)

def delete_docs_by_ids(repo, docids):
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

def bulk_add_or_replace_docs(repo, docs):
    bulk_data = []
    N = 1000
    TIMEOUT = 300
    for d in docs:
        docid = d['docid']
        content = d['content']

        op_dict = {
            "index": {
                "_index": INDEX_NAME,
                "_type": repo.name,
                '_id': docid
            }
        }
        data_dict = {
            'docid':docid,
            'url': d.get('url', ''),
            'ref': d.get('ref', ''),
            'created': d.get('created'),
            'content': content,
            'processing': d.get('processing'),
            'result': d.get('result', {}),
            'markup_partners' : d.get('markup_partners', {}),
            'regexp_partners' : d.get('regexp_partners', {})
        }
        bulk_data.append(op_dict)
        bulk_data.append(data_dict)
        if len(bulk_data) > N:
           res = es.bulk(index = INDEX_NAME, body = bulk_data, refresh = True, timeout=TIMEOUT)
           bulk_data = []

    if len(bulk_data) > 0:
       res = es.bulk(index = INDEX_NAME, body = bulk_data, refresh = True, timeout=TIMEOUT)

# document retrieval

def get_doc(repo, id):
    res = es.get(index = INDEX_NAME, doc_type = repo, id = id, _source = True)
    return res.get('_source', None)

def get_docs_by_ids(repo, doc_ids):
    res = es.mget(index = INDEX_NAME, doc_type = repo, body = { 'ids' : list(doc_ids) }, _source = True)
    print(str(res))
    return [d['_source'] for d in res['docs'] if d['found']]

def search(repo, query, r_from, r_size):
    res = es.search(
        index = INDEX_NAME,
        doc_type = repo,
        body = {
            'size': r_size,
            'query': {
                'constant_score': {
                   'query': {
                       'query_string' : { 'query' : query }
                   }
                }
            },
            'from': r_from
        })
    return res

def search_scan(repo):
    INDEX_NAME = 'elem'
    res = es.search(
        index = INDEX_NAME,
        doc_type = repo,
        search_type = 'scan',
        scroll = '10h',
        body = {
            'size': 10000,
            'query' : {
                'match_all' : {}
            }
        })
    return res

def scroll(scroll_id):
    res = es.scroll(
        scroll_id=scroll_id,
        scroll='10h'
    )
    return res

