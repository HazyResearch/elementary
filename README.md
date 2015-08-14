Elementary
==========

Documentation for customers is in `resources/templates/index.html`. Here are commands for admins:

*   Creating/Deleting a user account

    Visit `https://api.deepdivedata.org/users/` in your browser. Alternatively, use curl:

    ```bash
    curl -X POST \
        -u $ADMINUSER:$ADMINPASSWORD \
        -d username=$USERNAME -d password=$PASSWORD -d email=$EMAIL
        https://api.deepdivedata.org/users/
    ```

    ```bash
    curl -X DELETE \
        -u $ADMINUSER:$ADMINPASSWORD \
        https://api.deepdivedata.org/users/$USERNAME/
    ```

    NOTE: Deleting a user account cascades to all of the user's content, including
    repositories and documents. There is no undo.

*   Getting API token (optional)

    ```bash
    curl -X POST \
        -d username=$USERNAME -d password=$PASSWORD \
        https://api.deepdivedata.org/api-token-auth/
    ```
    From then on you use `-H 'Authorization: Token <TOKEN>'` for authentication, instead
    of `-u $USERNAME:$PASSWORD`.

*   Creating a repository

    ```bash
    curl -X POST \
        -u $USERNAME:$PASSWORD \
        -d name=$REPOSITORY \
        -d pipeline=memex/atf \
        https://api.deepdivedata.org/repos/
    ```

*   Deleting a repository

    ```bash
    curl -X DELETE \
        -u $USERNAME:$PASSWORD \
        https://api.deepdivedata.org/repos/$USERNAME/$REPOSITORY/
    ```

*   Submitting a single document to a repository

    ```bash
    // from web
    URL=http://yahoo.com
    CONTENT=`curl -sL $URL`
    DOCID=doc16

    // from tsv
    SOURCE=`head -1 input.tsv`
    DOCID=`echo "$SOURCE" | cut -f 1`
    JSON=`echo "$SOURCE" | cut -f 2`
    URL=`echo "$JSON" | jq -r '.url'`
    CONTENT=`echo $JSON | jq -r '.content'`

    curl -X POST \
         -u $USERNAME:$PASSWORD \
         -d docid="$DOCID" \
         --data-urlencode doc_url="$URL" \
         --data-urlencode content="$CONTENT" \
         https://api.deepdivedata.org/docs/$USERNAME/$REPOSITORY/
    ```

*   Submitting a batch of documents to a repository

    ```bash
    curl -X POST \
         -u $USERNAME:$PASSWORD \
         --data-urlencode source_url="http://api.deepdivedata.org/static/source.json" \
         https://api.deepdivedata.org/sources/$USERNAME/$REPOSITORY/
    ```

*   Fetching all documents of a repository

    ```bash
    curl -s -u $USERNAME:$PASSWORD \
         https://api.deepdivedata.org/docs/$USERNAME/$REPOSITORY/
    ```

    This returns a large json object with information about
    all documents; if you would like to only get the URLs you
    can do:

    ```bash
    curl -s -u $USERNAME:$PASSWORD \
         https://api.deepdivedata.org/docs/$USERNAME/$REPOSITORY/ | jq .results[].url
    ```

*   Fetching results for a single document

    ```bash
    curl -s -u $USERNAME:$PASSWORD \
         https://api.deepdivedata.org/docs/$USERNAME/$REPOSITORY/$DOCID/ | jq .result
    ```

*   Search by keyword

    ```bash
    curl -k -u $USERNAME:$PASSWORD https://localhost/docs/$USERNAME/$REPOSITORY/search/?q=KEYWORD
    curl -k -u $USERNAME:$PASSWORD "https://localhost/docs/$USERNAME/$REPOSITORY/search/?q=great&from=0&size=0"
    ```


### Deployment

This section describes the steps necessary to deploy the API to an ec-2 instance.

*  Launch instance

   Use at least m3.xlarge with Ubuntu 14.04. Make the boot volume at least 100GB and
   open ports 80 and 443.

*  Create user eve

   ```
   sudo adduser eve
   sudo visudo
   ```
   Grant sudo rights to eve by adding the following line
   ```
   eve    ALL=(ALL) NOPASSWD: ALL
   ```

   You might also want to copy `/home/ubuntu/.ssh/authorized_keys` to `/home/eve/.ssh/authorized_keys` to allow logging in as eve with your ssh key.
   ```
   sudo cp -r ~/.ssh /home/eve
   sudo chown -R eve:eve /home/eve/.ssh
   ```
   Now login as eve.

*  Run installers

   Most components required by elementary will run under user eve, and will be
   stored at `/opt`. For git permission, set your email and username.
   ```
   EMAIL="your.email@xyz.com"
   NAME="username"
   ```
   Now run:
   ```
   sudo chown eve:eve /opt
   cd /opt
   sudo apt-get install -y git
   git config --global credential.helper "cache --timeout=3600"
   git config --global user.email "$EMAIL"
   git config --global user.name "$NAME"

   ```
   
   Now clone following repositories into `/opt`:
   - elementary
   - elementary-memex
   - parser
   - pgxl

   ```
   cd /opt/services/parser
   ./setup.sh
   cd /opt/services/pgxl
   ./setup.sh
   ```
   The installer for pgxl will ask for several parameters. The default
   settings should work: The data directory will be on the instance store
   (deleted on reboot, but higher performance than EBS), the number of data
   nodes should not exceed the amount of memory / 2GB. We use port 6432
   (not 5432) for pgxl to avoid clashing with Postgres.

   ```
   cd /opt/elementary
   ./setup.sh
   cd /opt/elementary-memex
   ./setup.sh
   ```
   Nginx will fail without a valid SSL certificate. You can create a self-signed
   certificate for testing.
   ```
   sudo mkdir /etc/nginx/ssl
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" \
     -keyout /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.crt
   sudo service nginx restart
   sudo service supervisor start
   ```

   Install DeepDive with its dependencies.
   ```
   cd /opt
   bash <(curl -fsSL deepdive.stanford.edu/install)
   2
   4
   3
   q
   cd deepdive
   git fetch
   git checkout raphael-pgxl-multinomial
   make
   ```

*  Learn weights for extractors or copy them over.

   ```
   cd /opt/elementary-memex/escort
   ./learn.sh
   ```

### Debugging

*   Restarting celery
    ```
    sudo supervisorctl
    restart celery-docs
    ```
*   Celery logs
    ```
    tail -f /opt/elementary/logs/celery-docs.log
    ```

*   You can run django and celery manually (in seperate shells):
    ```
    python django/manage.py runserver
    celery worker --workdir django -l info -A elementary -c 1 -Q docs
    celery worker --workdir django -l info -A elementary -c 1 -Q sources
    ```
    If you would like to access django remotely append 0.0.0.0:8000
    (and open port in aws console).

*   Creating/removing super user accounts

    ```
    cd /opt/elementary
    source env/bin/activate
    python django/manage.py createsuperuser
    ```

*   Running tests

    ```
    python django/manage.py test resources
    ```

*   Updating DB schema

    ```
    python django/manage.py migrate
    ```
*   Purging the elementary queue
    ```
    /opt/elementary$ /opt/elementary/env/bin/celery purge --workdir /opt/elementary/django -A elementary
    ```
    
*   Logging into postgres database
    ```
    psql -h 127.0.0.1 -U eve elem
    ```

* Currently if a hyphen `-` is specified in creating a repo, the server will crash. In this case, look into the postgres database to fix it:
* 
    ```
    /usr/bin/psql -p5432 elem
    select * from resources_repository;
    ```

    Find the repo name that causes the problem. e.g.:

    ```
    id |     name      |            created            | owner_id |      pipeline
    ----+---------------+-------------------------------+----------+---------------------
      1 | atf           | 2015-08-13 22:45:26.799028+00 |        2 | memex/atf
      2 | escort        | 2015-08-13 22:57:03.825788+00 |        2 | memex/escort
      3 | review        | 2015-08-14 01:15:38.64802+00  |        2 | memex/escort-review
      4 | escort-review | 2015-08-14 01:41:24.176763+00 |        2 | memex/escort-review
    ```
    
    Delete the row from this table:
    
    ```
    DELETE from resources_repository WHERE id=4;
    ```

### Analyzing Query Logs

The most important file is ```/opt/elementary/logs/access.log```.

To get the number of document uploads by user, you can run
```
cat access.log | sed -n 's/.*POST \/docs\/\([a-z]*\)\/.*/\1/p' > docs_posts
sort docs_posts | uniq --count
```

Similary, you can get ```POST /sources/``` and ```GET /search/``` requests.


