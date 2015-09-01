#curl -XGET 'http://localhost:9200/elem/_search?q=aaaaaaaaaaxxxxxx'

curl -XGET 'http://localhost:9200/elem/_search?q=repo%3Arepo10'
#%20AND%20Kristina'
#curl -XGET 'http://localhost:9200/elem/_search?q=repo:repo7%20AND%20%22adultsearch%3A10002%22'
