# -*- coding: utf-8 -*-
import codecs
import errno
import io
import json
import logging
import multiprocessing
import os
import shutil
import sys
from subprocess import Popen

from resources.dataio import parse_docs

logger = logging.getLogger(__name__)


# tmp dir with respect to elementary root
TMP_DIR = 'tmp'
NUM_CORES = multiprocessing.cpu_count()


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def elementary_root():
    return os.path.dirname(os.path.realpath(__file__)) + '/../../..'


def run_pipeline(task_id, repo, docs):
    task_dir = elementary_root() + '/' + TMP_DIR + '/' + str(task_id)
    # pipelines are currently "memex/atf" and "memex/escort"
    pipeline_dir = elementary_root() + '/elementary-' + repo.pipeline

    # create task directory
    mkdir_p(task_dir)
    logger.info(task_dir)

    with io.open(task_dir + '/' + 'input.json', 'w', encoding='utf-8') as f:
        for d in docs:
            
            data = {
                'id': d['_id'],
                'url': d.get('url', ''),
                'content': d.get('content', '')
            }
            f.write(unicode(json.dumps(data, encoding='utf-8')) + '\n')

    # run scraper
    p1 = Popen(pipeline_dir + '/scrape.sh', cwd=task_dir)
    p1.communicate()  # wait

    # run NLP parser
    docs_content = []
    with codecs.open(os.path.join(task_dir, 'scraped.json'), 'r', 'utf-8') as f:
        for line in f:
            fields = json.loads(line)
            docs_content.append([fields['id'], fields['content']])

    docs_parsed = parse_docs(docs_content, num_threads=max(1, NUM_CORES - 1))

    # push parsing results into the input json objects
    blob_map = {str(x): y for x, y in docs_parsed}
    for d in docs:
        if str(d['_id']) in blob_map:
            d['parse'] = blob_map[str(d['_id'])]

    # write parsing results to TSV file
    with codecs.open(os.path.join(task_dir, 'parsed.tsv'), 'w', 'utf-8') as f:
        for docid, blob in docs_parsed:
            f.write(blob)

    # run inference
    p3 = Popen(pipeline_dir + '/infer.sh', cwd=task_dir)
    p3.communicate()  # wait

    # results are now in task_dir/result.json
    # the _ids here are mongo's internal IDs (unique and allow efficient updates)
    
    
    results = {}
    with open(task_dir + '/result.json', 'r') as f:
        for line in f:
            j = json.loads(line)
            _id = j['doc_id']
            del j['doc_id']
            results[str(_id)] = j

    for d in docs:
        _id = str(d['_id'])
        if _id in results:
            d['result'] = results[_id]
    '''
    result_ismassageparlorad = {}
    with open(task_dir + '/ismassageparlorad.json', 'r') as f:
        for line in f:
            j = json.loads(line)
            _id = j['doc_id']
            del j['doc_id']
            result_ismassageparlorad[str(_id)] = j

    result_issexad = {}
    with open(task_dir + '/issexad.json', 'r') as f:
        for line in f:
            j = json.loads(line)
            _id = j['doc_id']
            del j['doc_id']
            result_issexad[str(_id)] = j

    result_rates = {}
    with open(task_dir + '/rates.json', 'r') as f:
        for line in f:
            j = json.loads(line)
            _id = j['doc_id']
            del j['doc_id']
            result_rates[str(_id)] = j

    for d in docs:
        _id = str(d['_id'])
        tmp = {}
        if _id in result_ismassageparlorad:
            tmp['is_massage_parlor_ad'] = result_ismassageparlorad[_id]
        else:
            tmp['is_massage_parlor_ad'] = ""
        if _id in result_issexad:
            tmp['is_sex_ad'] = result_issexad[_id]
        else:
            tmp['is_sex_ad'] = ""
        if _id in result_rates:
            tmp['rates'] = result_rates[_id]
        else:
            tmp['rates'] = ""
        d['result'] = tmp
    '''
    shutil.rmtree(task_dir)
