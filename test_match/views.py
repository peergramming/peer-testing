import django_comments.models as cm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import render
from django.urls import reverse

import common.models as m
import common.permissions as cp
import test_match.permissions as p
import feedback.helpers as fh
from common.views import redirect


@login_required()
def test_match_view(request, test_match_id):
    """Render the page that allows a user to give feedback to a certain
    @test_match_id, and see all files associated with it"""
    test_match = m.TestMatch.objects.filter(id=test_match_id).first()
    if test_match is None:
        return Http404("No test match with that ID exists")
    perm = p.user_feedback_mode(request.user, test_match)
    if perm == p.TestMatchMode.DENY:
        return HttpResponseForbidden("You are not allowed to see this test data")
    redir_path = "view_cw" if cp.is_teacher(request.user) else "cw"
    if perm == p.TestMatchMode.WAIT:
        return redirect(request, "Please wait until the test has finished running",
                        reverse(redir_path, args=[test_match.coursework.id]))
    crumbs = [
        ("Homepage", reverse("teacher_index")),
        ("Coursework", reverse(redir_path, args=[test_match.coursework.id]))
    ]
    group = fh.feedback_group_for_test_match(test_match)
    comment_list = [(c.submit_date, c.comment,
                    fh.nick_for_comment(c.user, group, request.user))
                    for c in cm.Comment.objects.filter(object_pk=test_match_id)]
    names = fh.detail_test_match_anon_names(request.user, test_match, group)
    details = {
        "test_match": test_match,
        "solution_name": names[1],
        "test_name": names[2],
        "can_submit": perm == p.TestMatchMode.WRITE,
        "test_files": test_match.test.get_files(test_match.test_version),
        "result_files": test_match.result.get_files(),
        "solution_files": test_match.solution.get_files(test_match.solution_version),
        "user_owns_test": test_match.test.creator == request.user,
        "user_owns_sol": test_match.solution.creator == request.user,
        "crumbs": crumbs,
        "comment_list": comment_list
    }
    return render(request, 'test_match/feedback.html', details)
