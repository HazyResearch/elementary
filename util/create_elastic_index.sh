curl -XPOST localhost:9200/elem -d '{
    "settings" : {
        "number_of_shards" : 8
    },
    "mappings" : {
    }
}'
