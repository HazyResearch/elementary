#curl -XGET 'http://localhost:9200/elem/_search?q=repo:repo7'
curl -XGET 'http://localhost:9200/elem/_search?q=repo:repo7%20AND%20id:56%20AND%20result.incall:false'
