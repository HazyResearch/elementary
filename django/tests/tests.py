from django.test import TestCase
from django.contrib.auth.models import User
from django.test import Client

from resources.models import Repository
from resources.models import Document

# Create your tests here.

class UserTestCase(TestCase):

    def test_create_remove(self):
        # Create a user
        user1 = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
        self.assertIsNotNone(user1)
        # Remove user
        user2 = User.objects.get_by_natural_key('john')
        self.assertEqual(user1, user2)
        User.delete(user2)

class RepositoryTestCase(TestCase):

    def setUp(self):
        user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')

    def test_create_remove(self):
        # Create a repo
        repo = Repository.objects.create(name='myrepo') #, owner=User.objects.get(username='john'))
        self.assertIsNotNone(repo)
        # Remove repo
        Repository.delete(repo)

class DocumentTestCase(TestCase):

    def setUp(self):
        user = User.objects.create_user('john', 'lennon@thebeatles.com', 'johnpassword')
        self.repo = Repository.objects.create(name='myrepo') #, owner=User.objects.get(username='john'))

    def test_add_doc(self):
        # Add a document to the repo
        doc = Document.objects.create(docid='mydoc', repo=self.repo)
        # Query repo
        qds = self.repo.docs.filter(docid='mydoc')
        # Remove document from repo
        Document.delete(qds.first())

class ServerTestCase(TestCase):

    def setUp(self):
       user = User.objects.create_user('fred', '', 'secret')
       repo = Repository.objects.create(name='myrepo')
       doc = Document.objects.create(docid='mydoc', content='blah', repo=repo)

       self.c = Client()
       success = self.c.login(username='fred', password='secret')
       print(success)

       

    def test_request(self):
       #response = self.c.post('/login/', {'username': 'john', 'password': 'smith'})
       #print(response.status_code)
       response = self.c.get('/repos/')
       print( response.content)

    def test_pull(self):
       response = self.c.get('/docs/myrepo/all/')
       content = "".join([x for x in response.streaming_content]) 
       print('streaming content:')
       print(content)
       print(response)
