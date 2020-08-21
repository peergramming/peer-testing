import os
import tempfile
import shutil
import subprocess
import re
import hashlib

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import common.forms as f
import common.models as m
import feedback.helpers as fh
import feedback.enrol_to_group as fenrol
import runner.runner as r
import student.helper as h
from common.views import redirect
from test_match import matcher
from common.permissions import coursework_access
import common.notify as n
import main.local as local

import requests

import logging
logger = logging.getLogger("django")


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


@login_required()
def index(request):
    return detail_coursework(request)

# OLD submissions
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
        msg = re_version_submission(request, cw, old_sub)
    else:
        if file_type == m.SubmissionType.SOLUTION:
            msg = save_new_solution(request, cw)
        else:
            msg = save_new_test(request, cw)
    return redirect(request, "Upload completed." + msg, reverse("cw", args=[cw.id]))

# GITLAB Submissions
class GitlabFetcher:
    """Context manager which handles fetching gitlab files"""
    def __init__(self, user, project):
        """user A user object from django
        @path A string project name in gitlab
        Will be joined to fetch from /user/project in gitlab"""
        self.user = user
        self.path = str(user) + '%2F' + str(project)
        self.has_fetched = False
        self.tmp_dir = None

    def fetch_and_unpack(self):
        """fetch all the files from an archive and unpack them
        to a temporary directory. use the context manager to
        auto clean up
        @returns a string of the tmp dir location"""
        if self.has_fetched == True:
            return self.tmp_dir
        social = self.user.social_auth.get(provider='gitlab')
        gitlab_api_projects = local.SOCIAL_AUTH_GITLAB_API_URL + '/api/v4/projects/'
        gitlab_params = {'access_token': social.extra_data['access_token']}
        # Adding Peer-Testing to project as Reporter
        logger.info("Add Peer-Testing as Raporter to " + self.path)
        gitlab_add_pt_rep_data = { 'user_id' : local.GITLAB_PT_USER_ID,
                                    'access_level' : local.GITLAB_PT_USER_ACCESS_LEVEL }
        gitlab_add_pt_rep_req = gitlab_api_projects + self.path + "/members"
        resp_add_pt_rep = requests.post(gitlab_add_pt_rep_req,
                                        data=gitlab_add_pt_rep_data,
                                        params=gitlab_params,
                                        verify=False)
        logger.info("Add Peer-Testing as Raporter to %s: %s" % (self.path, resp_add_pt_rep.content))
        # Fetching archive
        gitlab_archive_req = gitlab_api_projects + self.path + "/repository/archive.tar.gz"
        response = requests.get(gitlab_archive_req,
                                params=gitlab_params,
                                verify=False)
        gitlab_info = str(response.__dict__)
        content=response.content
        self.tmp_dir = tempfile.mkdtemp()
        logger.info("Extracting files in dir: " + self.tmp_dir)
        tmp_archive_file_name = "archive.tar.gz"
        tmp_archive_file = os.path.join(self.tmp_dir, tmp_archive_file_name)
        with open(tmp_archive_file, "wb") as file:
            file.write(content)
        shutil.unpack_archive(tmp_archive_file, self.tmp_dir)
        os.remove(tmp_archive_file)
        self.has_fetched = True
        return self.tmp_dir

    def check_for_changes(self, old_submission, coursework, file_type):
        """check if the @file_type files in @old_submission object for @coursework have been
        changed in the newer upload and @return if so bool
        Checks file names, sizes and hashes"""
        path_re = coursework.test_path_re if file_type == m.SubmissionType.TEST_CASE else coursework.sol_path_re
        new_files = []
        old_files = old_submission.get_files()
        old_sub_path = old_submission.originals_path()
        with cd(self.tmp_dir):
            for dirpath, dirs, files in os.walk(os.getcwd()):
                for file_name in files:
                    if re.search(path_re, file_name):
                        new_file_path = os.path.join(dirpath,file_name)
                        # check for new file name
                        if file_name not in old_files:
                            return True
                        new_files.append(file_name)
                        old_file_path = os.path.join(old_sub_path, file_name)
                        # check file sizes
                        if os.stat(old_file_path).st_size != os.stat(new_file_path).st_size:
                            return True
                        # check file hashes
                        with open(old_file_path, 'rb') as f:
                            old_sha = hashlib.sha256()
                            old_sha.update(f.read())
                        with open(new_file_path, 'rb') as f:
                            new_sha = hashlib.sha256()
                            new_sha.update(f.read())
                        if old_sha.hexdigest() != new_sha.hexdigest():
                            return True
        # check intersection lengths to check for removed files
        return len(set(old_files) & set(new_files)) != len(old_files)

    def copy_gitlab_files_to_submission(self, submission, cw, file_type):
        """copy new version of files from temp directory
        to the @submission object for coursework @cw, given
        a specific @file_type of submission"""
        file_copied=False
        path_re = cw.test_path_re if file_type == m.SubmissionType.TEST_CASE else cw.sol_path_re
        with cd(self.tmp_dir):
            for dirpath, dirs, files in os.walk(os.getcwd()):
                for file_name in files:
                    if re.search(path_re, file_name):
                        submission.copy_file(os.path.join(dirpath,file_name))
                        file_copied=True
        if not file_copied:
            error_notification_file = os.path.join(self.tmp_dir, "NO_FILE_FETCHED_FROM_GITLAB")
            with open(error_notification_file, "wb") as file:
                file.write("NO_FILE_FETCHED_FROM_GITLAB")
            submission.copy_file(error_notification_file)

    def __enter__(self):
        if not self.has_fetched:
            self.fetch_and_unpack()
        return self

    def __exit__(self, etype, value, traceback):
        if self.has_fetched:
            logger.info("Removing dir: " + self.tmp_dir)
            shutil.rmtree(self.tmp_dir)
            self.has_fetched = False
            self.tmp_dir = None


# OLD submissions
@transaction.atomic
def re_version_submission(request, cw, submission):
    submission.increment_version()
    for each in request.FILES.getlist('chosen_files'):
        submission.save_uploaded_file(each)
    return "New version of files for '%s' has been uploaded. You should re-run " \
           "any tests again to use the new version." % submission.display_name


def save_new_solution(request, cw):
    name = "Solution"
    sub = save_new_submission(cw, request, m.SubmissionType.SOLUTION, name)
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


def save_new_test(request, cw):
    """Save the submission for the newly created test in
    @request for @cw"""
    current = count_highest_test(request.user, cw)
    name = "%s%s" % (TEST_DISP_NAME_PREFIX, str(current))
    save_new_submission(cw, request, m.SubmissionType.TEST_CASE, name)
    return "You can run your newly uploaded test against the oracle to make sure that you are " \
           "testing for the correct output. You can delete test cases that are not run against" \
           " anything yet."


@transaction.atomic
def save_new_submission(cw, request, file_type, name):
    """Do the atomic database actions required to save the new files"""
    submission = m.Submission(id=m.new_random_slug(m.Submission), coursework=cw,
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
    old_test = m.Submission.objects.filter(id=tid, creator=request.user).first()
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
        "allow_upload": cw.state in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK],
        "file_type": m.SubmissionType.SOLUTION,
        "cw": cw,
        "old_id": old_id,
        "crumbs": [("Homepage", reverse("student_index")),
                   ("Coursework", reverse("cw", args=[cw.id]))],
    }
    return render(request, 'student/upload_solution.html', detail)

# GITLAB submissions
@login_required()
@coursework_access
def gitlab_fetch(request, cw):
    """Given a @request to fetch a solution for @cw
    render the page or handle the requested fetch"""
    if request.POST:
        did_fetch = do_gitlab_fetch(request, cw)
        if request.POST['file_type'] == m.SubmissionType.SOLUTION and did_fetch:
            notify_peers_of_new_versions(request, cw)
        message = "Fetched latest files from GitLab" if did_fetch else "Latest files from GitLab are up to date"
        return redirect(request, message, reverse("cw", args=[cw.id]))
    else:
        return render_gitlab_fetch_page(request, cw)

def render_gitlab_fetch_page(request, cw):
    """Given a @request to upload a solution to @cw
    render the page that offers a way to fetch the latest
    versions of test and solution from gitlab"""
    has_solution = m.Submission.objects.filter(coursework=cw, creator=request.user,
                                         type=m.SubmissionType.SOLUTION).exists()
    has_test = m.Submission.objects.filter(coursework=cw, creator=request.user,
                                         type=m.SubmissionType.TEST_CASE).exists()
    if has_solution:
        submission_msg = "Fetch new version for Solution from GitLab-Student"
    else:
        submission_msg = "Fetch Solution for coursework from GitLab-Student"
    if has_test:
        test_msg = "Fetch new version for test case from GitLab-Student"
    else:
        test_msg = "Fetch Test Case for coursework from GitLab-Student"
    gitlab_repo = str(request.user) + "/" + str(cw.name)
    detail = {
        "submission_msg": submission_msg,
        "test_msg": test_msg,
        "allow_upload": cw.state in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK],
        "file_type_solution": m.SubmissionType.SOLUTION,
        "file_type_test": m.SubmissionType.TEST_CASE,
        "cw": cw,
        "crumbs": [("Homepage", reverse("student_index")),
                   ("Coursework", reverse("cw", args=[cw.id]))],
        "gitlab_repo" : gitlab_repo
    }
    return render(request, 'student/gitlab_fetch.html', detail)

@transaction.atomic
def do_gitlab_fetch(request, cw):
    """Given this @request to fetch files for @cw,
    fetch the files from gitlab.
    @return bool if anything was actually fetched"""
    file_type = request.POST['file_type']
    if not h.user_can_upload_of_type(request.user, cw, file_type):
        return HttpResponseForbidden("You can't upload submissions of this type")
    with GitlabFetcher(request.user, str(cw.name)) as gf:
        try:
            latest_submission = m.Submission.objects.get(coursework=cw, creator=request.user, type=file_type)
            if gf.check_for_changes(latest_submission, cw, file_type):
                latest_submission.increment_version()
                latest_submission.save()
                gf.copy_gitlab_files_to_submission(latest_submission, cw, file_type)
                return True
            return False
        except ObjectDoesNotExist as e:
            name = "Solution" if file_type == m.SubmissionType.SOLUTION else "Test Case"
            new_submission = m.Submission(id=m.new_random_slug(m.Submission), coursework=cw,
                creator=request.user, type=file_type,
                display_name=name)
            new_submission.save()
            gf.copy_gitlab_files_to_submission(new_submission, cw, file_type)
            return True

def notify_peers_of_new_versions(request, cw):
    """after a new solution has been uploaded, notify the peers in that group
    @cw coursework where new solution was uploaded to"""
    groups = fh.get_feedback_groups_for_user_in_coursework(request.user, cw)
    all_peer_users = []
    for group in groups:
        all_users_in_group = fh.get_all_users_in_feedback_group(group)
        all_peer_users += [str(u[0]) for u in all_users_in_group]
    all_peer_users_uniq = list(dict.fromkeys(all_peer_users))
    for peer_user in all_peer_users_uniq:
        cw_name = str(cw.name)
        url = request.build_absolute_uri(cw.id)
        logger.info("New Sol: " + str(request.user))
        logger.info("New Sol coursework: " + cw_name)
        logger.info("New Sol url: " + url)
        logger.info("New Sol peer:" + peer_user)
        n.add_notification(peer_user,cw,"New peer solution uploaded at " + url)

# Rest of student view methods
@login_required()
def detail_coursework(request, cw=None):
    """If a coursework @cw is specified,return the page detailing it
    otherwise return a listing of all currently available tasks. """
    fenrol.add_all_students_to_feedback_groups()
    if cw is None or cw == "":
        if len(local.RESEARCH_BLURB_RAW_HTML) > 0:
            return render(request, 'student/choose_coursework.html',
                {'courseworks': h.coursework_available_for_user(request.user),
                'has_research': True,
                'research_url': local.RESEARCH_QUESIONNAIRE_URL,
                'research_blurb': local.RESEARCH_BLURB_RAW_HTML})
        else:
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

    testing_data = detail_self_test_matches(request.user, cw) + detail_peer_feedback_group(request.user, cw)

    details = {
        "cw": cw,
        "descriptors": descriptors,
        "solution": sols,
        "tests": tests,
        "testing_data": testing_data,
        "subs_open": cw.state in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK],
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
    testable_sols = [(sol.id, sol.display_name + " (v" + str(sol.latest_version) + ")" ) for sol in m.Submission.objects.filter(
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
        (item.id, fh.nick_for_display(group, user, item, item.latest_version)) for item in
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
    #temp solution allowing self tests during peer test time
    if cw.state == m.CourseworkState.UPLOAD or request.POST['feedback_group'] == '':
        tm_form = generate_self_match_form(cw, user, post=request.POST)
    else:
        tm_form = generate_peer_match_form(cw, user,
                                           request.POST['feedback_group'], post=request.POST)
    if not tm_form.is_valid():
        logger.info("Form error: " + str(tm_form.errors))
        return HttpResponseForbidden("Invalid form data")
    if cw.state not in [m.CourseworkState.UPLOAD, m.CourseworkState.FEEDBACK]:
        return HttpResponseForbidden("This coursework isn't accepting new test matches")
    args = [
        tm_form.cleaned_data['solution'],
        tm_form.cleaned_data['test'],
        cw
    ]
    if cw.state == m.CourseworkState.UPLOAD or request.POST['feedback_group'] == '':
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
        return redirect(request, "Test Created", reverse("tm", args=[new_tm.id,'']))
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
