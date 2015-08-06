#!/bin/bash

if [ "$(whoami)" != "eve" ]; then
    echo 'Must run as the user "eve"'
    exit 1
fi

if [ ! -d "/opt/elementary" ]; then
    echo "Must have /opt/elementary (with content)"
    exit 1
fi


/opt/elementary/django/manage.py syncdb
/opt/elementary/django/manage.py migrate
/opt/elementary/django/manage.py collectstatic 

# supervisor
sudo ln -s /opt/elementary/conf/supervisor.conf /etc/supervisor/conf.d/elementary.conf
sudo service supervisor restart

sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.org
sudo ln -s /opt/elementary/conf/nginx* /etc/nginx/
sudo ln -s /opt/elementary/conf/ssl /etc/nginx/ssl
sudo service nginx restart

# firewall
sudo ufw allow 22
sudo ufw allow 443
sudo ufw allow 80
sudo ufw enable

# create elasticsearch index
source /opt/elementary/util/create_elastic_index.sh


# to copy data from one server to another:
# pg_dump --data-only elem | gzip > dump.sql.gz
# scp ...
# cat dump.sql.gz | gunzip | psql elem
