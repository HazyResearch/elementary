from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse
from django.http import StreamingHttpResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, mixins, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

from .models import Document, DocSource, Regexp, Repository
from .serializers import (DocumentSerializer, DocSourceSerializer,
    RegexpSerializer, RepositorySerializer, UserSerializer)
from bson import json_util
import json
import urllib
import urllib2

import logging

from .bulk import *

logger = logging.getLogger(__name__)

@login_required
def root(request):
    return render(request, 'index.html')


class AuthTokenView(ObtainAuthToken):
    def get(self, request):
        if not request.user.is_authenticated():
            return Response('Please use POST instead or log in from the browser first')

        token, created = Token.objects.get_or_create(user=request.user)
        return Response({'token': token.key})


class RepoPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False
        if request.method == 'POST' and not request.user.is_staff:
            return settings.ELEMENTARY_ALLOW_REPO_CREATION
        return True


class IsAdminOrSelf(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False
        if not request.user.is_staff:
            return request.method in ['GET', 'HEAD', 'OPTIONS', 'PUT']
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return request.user == obj


class IsAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        elif not 'repo' in view.kwargs:
            return False
        else:
            repo = _get_repo_from_view(view)
            if not repo:
                return False
            if not request.user.is_staff and request.user != repo.owner:
                return False
        return True


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrSelf]
    lookup_field = 'username'

    def get_queryset(self):
        user = self.request.user
        if not user.is_staff:
            return User.objects.filter(id=user.id)
        return User.objects.all()


class RepoViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all() #select_related('owner')
    serializer_class = RepositorySerializer
    permission_classes = [RepoPermission]
    #permission_classes = (IsAuthenticated,)
    lookup_field = 'name' #'full_name'
    lookup_value_regex = r'\w+' # r'\w+/\w+'

    def get_queryset(self):
        #user = self.request.user
        #if not user.is_staff:
        #    return Repository.objects.filter(owner=user)
        return Repository.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        #owner_name, name = self.kwargs['full_name'].split('/', 1)
        name = self.kwargs['name']
        #obj = get_object_or_404(queryset, name=name, owner__username=owner_name)
        obj = get_object_or_404(queryset, name=name)
        return obj

    def perform_create(self, serializer):
        serializer.save() #(owner=self.request.user)

    def perform_destroy(self, instance):
        # delete from elastic
        elastic_delete_repo(instance.name) 
        # delete from mongo
        mongo_delete_repo(instance.name)
        super(RepoViewSet, self).perform_destroy(instance)

class DocViewSet(viewsets.GenericViewSet,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin,
                 mixins.CreateModelMixin):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    #permission_classes = [IsAdminOrOwner]
    permission_classes = (IsAuthenticated,)
    renderer_classes = (JSONRenderer,BrowsableAPIRenderer,)
    lookup_field = 'docid'

    def get_queryset(self):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        return Document.objects.all().filter(repo=repo)
        #return _get_queryset_owned(Document, self)

    def get_object(self):
        queryset = self.get_queryset()
        docid = self.kwargs['docid']
        obj = queryset.filter(docid=docid).first()
        return obj

    def perform_create(self, serializer):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        kwargs = {}
        serializer.save(repo=repo, **kwargs)
        #_create_if_owned(self, serializer)

    def perform_destroy(self, instance):
        # delete from elasticsearch
        instance.delete_elastic_data()
        # delete from mongo
        instance.delete_mongo_data()
        # delete from postgres
        super(DocViewSet, self).perform_destroy(instance)

    @list_route()
    def search(self, request, repo):
        q = request.GET.get('q', '')
        r_from = int(request.GET.get('from', '0'))
        r_size = int(request.GET.get('size', '10'))

        data = {
          "query": {
            "query_string" : { "query" : q }
          },
          "filter": {
            "term" : { "repo" : repo }
          },
          "from" : r_from,
          "size" : r_size
        }

        url='http://127.0.0.1:9200/elem/docs/_search'
        data_enc = urllib.urlencode(data)
        req = urllib2.Request(url, json.dumps(data))
        response = urllib2.urlopen(req)
        the_page = response.read()
        return HttpResponse(the_page, content_type="application/json")

    def stream_response_generator(self, repo):
        collection = Document.get_mongo_collection()
        for d in collection.find({'repo':repo}, { 'docid':1, 'content':1, 'doc_url':1, 'result':1,
           'markup_partners':1, 'regexp_partners':1, 'created':'1', 'url':1, 'processing':1}):
           del d['_id']
           d['created'] = d['created'].strftime("%Y-%m-%d %H:%M:%S")
           yield json.dumps(d) + '\n'

    @list_route()
    def all(self, request, repo):
        resp = StreamingHttpResponse( self.stream_response_generator(repo), 
            content_type='text/plain')
        resp['Content-Disposition'] = 'attachment; filename="all.json"'
        return resp

    @detail_route(methods=['post', 'delete', 'get'])
    def markup(self, request, repo, docid):
        if request.method == 'POST':
	    doc = Document.objects.filter(repo=repo, docid=docid).first()
        
            data = {}
            try:
                data = json.loads(request.body)
            except Exception:
                return Response('Please put a valid JSON object into your POST request')           

            username = request.user.username
            doc.update_mongo_data({ '$set' : { 'markup_partners.' + username : data }})
            doc.update_elastic_data({ 'script' : 
                'ctx._source.markup_partners.' + username + '= newObj',
                'params' : { 'newObj' : data } })
            # note: the previous commands replace, the following merges
            #doc.update_elastic_data({ 'doc': {'markup_partners' : { username : data }}})
            return HttpResponse('ok')

        elif request.method == 'GET':
           return HttpResponse('not yet supported') 
        elif request.method == 'DELETE':
            # delete
            username = request.user.username
            doc = Document.objects.filter(repo=repo, docid=docid).first()
            doc.update_elastic_data({ "script" : 
                "ctx._source.markup_partners.remove(\"" + username + "\")" })
            doc.update_mongo_data({ '$unset' : { 'markup_partners.' + username : "" }})
            return HttpResponse('ok')


class DocSourceViewSet(viewsets.GenericViewSet,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin):

    queryset = DocSource.objects.all()
    serializer_class = DocSourceSerializer
    #permission_classes = [IsAdminOrOwner]
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        return DocSource.objects.all().filter(repo=repo)
        #return _get_queryset_owned(DocSource, self)

    def perform_create(self, serializer):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        kwargs = {}
        serializer.save(repo=repo, **kwargs)
        #_create_if_owned(self, serializer, {'creator': self.request.user})


class RegexpViewSet(viewsets.GenericViewSet,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin,
                 mixins.CreateModelMixin):

    queryset = Regexp.objects.all()
    serializer_class = RegexpSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        return Regexp.objects.all().filter(repo=repo)

    def perform_create(self, serializer):
        repo_name = self.kwargs.get('repo', None)
        repo = Repository.objects.filter(name=repo_name).first()
        kwargs = {'owner': self.request.user}
        serializer.save(repo=repo, **kwargs)



def _get_queryset_owned(model, view):
    queryset = model.objects.select_related('repo__owner')

    repo = _get_repo_from_view(view)
    user = view.request.user
    if not repo or not (user.is_staff or repo.owner == user):
        raise Http404

    queryset = queryset.filter(repo=repo)
    return queryset


def _create_if_owned(view, serializer, kwargs=None):
    repo = _get_repo_from_view(view)
    user = view.request.user
    if not user.is_staff and user != repo.owner:
        raise Http404
    if not kwargs:
        kwargs = {}
    serializer.save(repo=repo, **kwargs)

def _delete_if_owned(view, serializer, kwargs=None):
    repo = _get_repo_from_view(view)
    user = view.request.user
    if not user.is_staff and user != repo.owner:
        raise Http404
    if not kwargs:
        kwargs = {}
    serializer.destroy(repo=repo, **kwargs)

#def _update_if_owned(view, serializer, kwargs=None):
#    repo = _get_repo_from_view(view)
#    user = view.request.user
#    if not user.is_staff and user != repo.owner:
#        raise Http404
#    if not kwargs:
#        kwargs = {}
#    serializer.update(repo=repo, **kwargs)

def _get_repo_from_view(view):
    user_name = view.kwargs.get('user', None)
    repo_name = view.kwargs.get('repo', None)
    repo = Repository.objects.filter(name=repo_name,
                                     owner__username=user_name).first()
    return repo




