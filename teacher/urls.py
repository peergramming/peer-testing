from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url('login', auth_views.login, name='login'),
    url('logout', auth_views.logout, name='logout'),
    url('create_course', views.create_course, name='create_course'),
    url('course/(?P<c>[0-9a-zA-Z\-_]*)', views.edit_course, name='edit_course'),
    url('create_cw/(?P<c>[0-9a-zA-Z\-_]*)', views.create_coursework, name='create_cw'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/edit', views.edit_coursework, name='edit_cw'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/groups', views.edit_coursework_groups, name='edit_cw_groups'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/view_comments', views.view_coursework_comments, name='view_cw_comments'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/view_tms', views.view_coursework_tms, name='view_cw_tms'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/view_files', views.view_coursework_files, name='view_cw_files'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/timeline/(?P<s>[0-9a-zA-Z\-_]*)', views.view_timeline, name='timeline'),
    url('updatecontent/', views.update_content, name='update_content'),
    url('test_all/(?P<c>[0-9a-zA-Z\-_]*)', views.run_all_test_in_cw, name='run_all_test_in_cw'),
    url('cw/(?P<c>[0-9a-zA-Z\-_]*)/make_tm', views.create_test_match, name='make_tm'),
    url(r'^$', views.index, name='teacher_index'),
]
