
from django.conf.urls import url

from . import views

urlpatterns = [
    url('(?P<test_match_id>[0-9a-zA-Z\-_]*)(?P<commented>[@]*)', views.test_match_view, name='tm'),
]
