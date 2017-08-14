from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse

import common.forms as f
import common.models as m
import feedback.helpers as fh
import runner.runner as r
import student.helper as h
from common.views import redirect
from test_match import matcher
from common.permissions import coursework_access


@login_required()
def index(request):
    return detail_coursework(request)


@login_required()
@coursework_access
def upload_submission(request, cw):
    """Given a @request, handle a POST upload form
    for the specified coursework @cw."""
    if request.method != "POST":
        return HttpResponseForbidden("You can only POST a form here")
    file_type = request.POST['file_type']
    if not h.user_can_upload_of_type(request.user, cw, file_type):
        return HttpResponseForbidden("You can't upload submissions of this type")
    old_sub = m.Submission.objects.filter(id=request.POST['re_version']).first()
    if old_sub is not None:
        if old_sub.creator != request.user:
            return HttpResponseForbidden("You can't modify that submission")
        msg = re_version_submission(old_sub, request.FILES.getlist('chosen_files'))
    else:
        if file_type == m.SubmissionType.SOLUTION:
            msg = save_new_solution(request, cw)
        else:
            msg = save_new_test(request, cw)
    return redirect(request, "Upload completed." + msg, reverse("cw", args=[cw.id]))


@transaction.atomic
def re_version_submission(submission, new_files):
    submission.increment_version()
    for each in new_files:
        submission.save_uploaded_file(each)
    return "New version of files for '%s' has been uploaded. You should re-run " \
           "any tests again to use the new version." % submission.display_name


def save_new_solution(request, cw_instance):
    name = "Solution"
    sub = save_new_submission(cw_instance, request, m.SubmissionType.SOLUTION, name)
    r.run_signature_test(sub)
    return "Your solution has been tested using the signature test. You should check the " \
           "results of this test to make sure that our solution is written correctly "


TEST_DISP_NAME_PREFIX = "Test Case #"

def count_highest_test(user, coursework):
    """Count the number of tests @user has submitted for
    @coursework so we can find out what number to give
    to the new one. Recall some may be deleted, so
    x.count() is not accurate enough of a solution."""
    current = m.Submission.objects.filter(coursework=coursework, creator=user, type=m.SubmissionType.TEST_CASE)
    if current.count() == 0:
        return 1
    ids = [m.display_name[len(TEST_DISP_NAME_PREFIX):] for m in current]
    ids.sort()
    return int(ids[-1]) + 1


def save_new_test(request, cw_instance):
    """Save the submission for the newly created test in
    @request for @cw_instance"""
    current = count_highest_test(request.user, cw_instance)
    name = "%s%s" % (TEST_DISP_NAME_PREFIX, str(current))
    save_new_submission(cw_instance, request, m.SubmissionType.TEST_CASE, name)
    return "You can run your newly uploaded test against the oracle to make sure that you are " \
           "testing for the correct output. You can delete test cases that are not run against" \
           " anything yet."


@transaction.atomic
def save_new_submission(cw_instance, request, file_type, name):
    """Do the atomic database actions required to save the new files"""
    submission = m.Submission(id=m.new_random_slug(m.Submission), coursework=cw_instance,
                              creator=request.user, type=file_type,
                              display_name=name)
    submission.save()
    for each in request.FILES.getlist('chosen_files'):
        submission.save_uploaded_file(each)
    return submission


@login_required()
@coursework_access
def upload_test(request, cw, tid=None):
    """Given a @request to upload a test to @cw
    render the submission form for test cases"""
    old_test = m.Submission.objects.filter(id=tid).first()
    if old_test is None:
        msg = "Upload Test Case for coursework"
    else:
        msg = "Upload new version for " + old_test.display_name
    detail = {
        "msg": msg,
        "allow_upload": cw.state in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK],
        "file_type": m.SubmissionType.TEST_CASE,
        "cw": cw,
        "old_id": tid,
        "crumbs": [("Homepage", reverse("student_index")),
                   ("Coursework", reverse("cw", args=[cw.id]))]
    }
    return render(request, 'student/upload_solution.html', detail)


@login_required()
@coursework_access
def upload_solution(request, cw):
    """Given a @request to upload a solution to @cw
    render the submission form for solutions"""
    exists = m.Submission.objects.filter(coursework=cw, creator=request.user,
                                         type=m.SubmissionType.SOLUTION).first()
    if exists is None:
        msg = "Upload Solution for coursework"
        old_id = ""
    else:
        msg = "Upload new version for solution"
        old_id = exists.id
    detail = {
        "msg": msg,
        "allow_upload": cw.state == m.CourseworkState.UPLOAD,
        "file_type": m.SubmissionType.SOLUTION,
        "cw": cw,
        "old_id": old_id,
        "crumbs": [("Homepage", reverse("student_index")),
                   ("Coursework", reverse("cw", args=[cw.id]))]
    }
    return render(request, 'student/upload_solution.html', detail)


@login_required()
def detail_coursework(request, cw=None):
    """If a coursework @cw is specified,return the page detailing it
    otherwise return a listing of all currently available tasks. """
    if cw is None or cw == "":
        return render(request, 'student/choose_coursework.html',
                      {'courseworks': h.coursework_available_for_user(request.user)})
    return single_coursework(request, cw)


@coursework_access
def single_coursework(request, cw):
    """Given a @request for the details for
    coursework @cwid, generate the page"""
    descriptors = h.get_descriptor_tuples(cw)
    sols = h.get_solution_tuples(cw, request.user)
    tests = h.get_test_triples(cw, request.user)

    if cw.state == m.CourseworkState.UPLOAD:
        testing_data = detail_self_test_matches(request.user, cw)
    else:
        testing_data = detail_peer_feedback_group(request.user, cw)

    details = {
        "cw": cw,
        "descriptors": descriptors,
        "solution": sols,
        "tests": tests,
        "testing_data": testing_data,
        "subs_open": cw.state == m.CourseworkState.UPLOAD,
        "feedback_open": cw.state == m.CourseworkState.FEEDBACK,
        "crumbs": [("Homepage", reverse("student_index"))],

    }
    return render(request, 'student/detail_coursework.html', details)


def detail_self_test_matches(user, coursework):
    """For self testing for a @use rin a @coursework,
    prepare the match form and list results"""
    tms = [(tm, tm.solution.display_name, tm.test.display_name) for tm in
           m.TestMatch.objects.filter(type=m.TestType.SELF, coursework=coursework) if
           tm.solution.creator == user or tm.test.creator == user]
    match_form = generate_self_match_form(coursework, user)
    return [(match_form, tms, "Self-Testing", """
<ul>
    <li>You can run your tests here to make sure that your solution is working correctly</li>
    <li>You can also run your tests against the oracle to see what a correct solution does</li>
</ul>
    """)]


def detail_peer_feedback_group(user, coursework):
    """For each feedback @group that @user is a member of,
    in a given @coursework, collect the relevant files, 
    generate the form and list the test match results"""
    tm_groups = fh.get_feedback_groups_for_user_in_coursework(user, coursework)
    testing_data = []
    section_title = "Peer-Testing Group %s"
    section_description = """
<ul>
<li>You can test the solutions of your peers and use their tests on your own solution</li>
<li>You can then give and receive feedback for individual test results</li>
<li>Including you, there are %s peers in this feedback group</li>
</ul>
    """
    for group in tm_groups:
        tms = fh.get_all_test_matches_in_feedback_group(user, group)
        match_form = generate_peer_match_form(coursework, user, group)
        members = fh.count_members_of_group(group)
        testing_data.append((match_form, tms, section_title % group.id,
                             section_description % members))
    return testing_data


def generate_self_match_form(cw, user, post=None):
    """Given a @cw instance, an @user, generate the easy
    test match form for self testing purposes.
    If the form is to be used in validating a @post request,
    this may also be passed in"""
    usable_tests = [(test.id, test.display_name) for test in m.Submission.objects.filter(
        coursework=cw, creator=user, type=m.SubmissionType.TEST_CASE)]
    testable_sols = [(sol.id, sol.display_name) for sol in m.Submission.objects.filter(
        coursework=cw, creator=user, type=m.SubmissionType.SOLUTION)]
    sig = m.Submission.objects.get(coursework=cw, type=m.SubmissionType.SIGNATURE_TEST)
    usable_tests.append((sig.id, sig.display_name))
    orc = m.Submission.objects.get(coursework=cw, type=m.SubmissionType.ORACLE_EXECUTABLE)
    testable_sols.append((orc.id, orc.display_name))
    if post is None:
        return f.EasyMatchForm(usable_tests, testable_sols)
    return f.EasyMatchForm(usable_tests, testable_sols, post)


def generate_peer_match_form(cw, user, group, post=None):
    """Given a @cw instance, an @user, generate the easy
    test match form for peer testing purposes.
    If the form is to be used in validating a @post request,
    this may also be passed in"""
    all_users = fh.get_all_users_in_feedback_group(group)
    user_objects = [item[0] for item in all_users]
    all_sols = m.Submission.objects.filter(coursework=cw,
                                           creator__in=user_objects,
                                           type=m.SubmissionType.SOLUTION)
    tests = [(t.id, t.display_name) for t in
             m.Submission.objects.filter(coursework=cw, creator=user,
                                         type=m.SubmissionType.TEST_CASE)]
    sols = [
        (item.id, fh.nick_for_display(group, user, item)) for item in
        m.Submission.objects.filter(coursework=cw,
        creator__in=user_objects,
        type__in=m.SubmissionType.SOLUTION)
    ]
    sig = m.Submission.objects.get(coursework=cw, type=m.SubmissionType.SIGNATURE_TEST)
    tests.append((sig.id, sig.display_name))
    orc = m.Submission.objects.get(coursework=cw, type=m.SubmissionType.ORACLE_EXECUTABLE)
    sols.append((orc.id, orc.display_name))
    if post is None:
        return f.EasyMatchForm(tests, sols, initial={"feedback_group": group.id})
    return f.EasyMatchForm(tests, sols, post)


@login_required()
@coursework_access
def create_new_test_match(request, cw):
    """Given a coursework id, @cw, this is an entry point into creating
    a new test match, which will then be run"""
    user = request.user
    if not request.POST:
        return HttpResponseForbidden("You're supposed to POST a form here")
    if cw.state == m.CourseworkState.UPLOAD:
        tm_form = generate_self_match_form(cw, user, post=request.POST)
    else:
        tm_form = generate_peer_match_form(cw, user,
                                           request.POST['feedback_group'], post=request.POST)
    if not tm_form.is_valid():
        return HttpResponseForbidden("Invalid form data")
    if cw.state not in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK]:
        return HttpResponseForbidden("This coursework isn't accepting new test matches")
    args = [
        tm_form.cleaned_data['solution'],
        tm_form.cleaned_data['test'],
        cw
    ]
    if cw.state == m.CourseworkState.UPLOAD:
        method = matcher.create_self_test
    else:
        method = matcher.create_peer_test
        args.append(tm_form.cleaned_data['feedback_group'])
        if not fh.user_is_member_of_group(user, tm_form.cleaned_data['feedback_group']):
            return HttpResponseForbidden("You're not a member of that feedback group")
    args.append(user)
    try:
        new_tm = method(*args)
        r.run_test_on_thread(new_tm)
        return redirect(request, "Test Created", reverse("tm", args=[new_tm.id]))
    except Exception as e:
        return HttpResponseForbidden(str(e))


@login_required()
@transaction.atomic()
def delete_submission(request):
    """A user has requested deletion of a file, with id in post"""
    sub_id = request.POST['sub_id']
    cw = m.Submission.objects.get(id=sub_id).coursework
    status = h.delete_submission(request.user, m.Submission.objects.get(id=sub_id))
    if status:
        return redirect(request, "Submission Deleted", reverse("cw", args=[cw.id]))
    return redirect(request, "Failed to delete file", reverse("cw", args=[cw.id]))
