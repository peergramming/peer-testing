from django.conf.urls import url

from . import views

urlpatterns = [
    url('(?P<sub_id>[0-9a-zA-Z\-_]*)/(?P<version>[0-9]*)/(?P<filename>[0-9a-zA-Z\-_.]*)',
        views.download_versioned_file,
        name='download_versioned_file'),
    url('(?P<sub_id>[0-9a-zA-Z\-_]*)/(?P<filename>[0-9a-zA-Z\-_.]*)',
        views.download_file,
        name='download_file'),
]
