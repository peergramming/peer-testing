from django.conf.urls import url

from . import views

urlpatterns = [
    url('modify', views.modify, name='modify_feedback_group'),
    url('delete', views.delete, name='delete_feedback_group'),
    url('export', views.export_data, name='export_feedback_groups'),
    url('import', views.import_data, name='import_feedback_groups')
]
