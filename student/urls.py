from django.conf.urls import url

from . import views

urlpatterns = [
    url('cw/(?P<cw>[0-9a-zA-Z\-_]*)/solution', views.upload_solution, name='solution'),
    url('cw/(?P<cw>[0-9a-zA-Z\-_]*)/test/(?P<tid>[0-9a-zA-Z\-_]*)', views.upload_test, name='test'),
    url('cw/(?P<cw>[0-9a-zA-Z\-_]*)/submit', views.upload_submission, name='submit'),
    url('cw/(?P<cw>[0-9a-zA-Z\-_]*)/make_tm', views.create_new_test_match, name='make_tm_student'),
    url('cw/(?P<cw>[0-9a-zA-Z\-_]*)', views.detail_coursework, name='cw'),
    url('delsub', views.delete_submission, name='delsub'),
    url(r'^$', views.index, name='student_index'),
]
