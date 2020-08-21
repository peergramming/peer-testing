from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import subprocess
import common.permissions as cp
from common.views import redirect

@login_required()
def default_index(request):
    """Redirect to index page depending on role"""
    if cp.is_teacher(request.user):
        return redirect(request, 'You are being redirected to the teacher page', reverse("teacher_index"))
    else:
        return redirect(request, 'You are being redirected to the student page', reverse("student_index"))
