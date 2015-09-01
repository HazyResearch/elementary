from base import *
DEBUG = True
LOGGING['root']['level'] = 'DEBUG'

try:
    from .dev_local import *
except:
    pass

MONGO_DB_NAME = 'model_data'
ELASTIC_INDEX_NAME = 'elem'
