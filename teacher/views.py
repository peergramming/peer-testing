from string import Template

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db import connection
from django.db import reset_queries
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
import django_comments.models as cm

import common.forms as cf
import common.models as m
import common.permissions as p
import feedback.forms as ff
import feedback.enrol_to_group as fenrol
import teacher.forms as f
from common.permissions import require_teacher
from common.views import redirect
from runner import runner as r
from test_match import matcher
import common.notify as n


@login_required()
@require_teacher
def index(request):
    """Show all of the courses available for the
    logged in teacher as a list"""
    enrolled_in = m.EnrolledUser.objects.filter(login=request.user)
    my_courses = [x.course for x in enrolled_in]
    detail = {
        "courses": my_courses
    }
    return render(request, 'teacher/index.html', detail)


@login_required()
@require_teacher
def create_course(request):
    """Handle the creation of a course, or create the form to do so"""
    if request.method == "POST":
        return create_course_update(request, request.POST)
    return create_course_render(request)


def create_course_render(request):
    """Generate the form used to create a course"""
    detail = {
        "course_name": "New Course",
        "courseworks": None,
        "uf": f.CourseForm({"student": str(request.user) + ','}),
        "crumbs": [("Homepage", reverse("teacher_index"))]
    }
    return render(request, 'teacher/edit_course.html', detail)


@transaction.atomic
def create_course_update(request, new_details):
    """Given the @new_details from a course, create a new course.
    Also handle enrolling all of the specified users. The
    owner of the course is not allowed to remove themselves"""
    owner = request.user
    updated_form = f.CourseForm(new_details)
    if not updated_form.is_valid():
        raise Exception("validity problem")
    new_code = updated_form.cleaned_data['code']
    new_name = updated_form.cleaned_data['name']
    new_students = updated_form.cleaned_data['student'].strip().strip(',').split(',')
    new_students_list = list(map(lambda w: w.strip(), new_students))

    course = m.Course(code=new_code, name=new_name)
    course.save()

    for item in new_students_list:
        current_user = m.User.objects.get(username=item)
        new_item = m.EnrolledUser(login=current_user, course=course)
        new_item.save()

    if str(owner) not in new_students_list:
        new_item = m.EnrolledUser(login=owner, course=course)
        new_item.save()

    return redirect(request, "Course created", reverse('edit_course', args=[new_code]))


@login_required()
@require_teacher
def edit_course(request, c):
    """Handle creation of form, or post request for editing a course"""
    cw = m.Course.objects.get(code=c)
    if not p.is_enrolled_on_course(request.user, cw):
        return HttpResponseForbidden("You are not enrolled on this course")
    if request.method == "POST":
        edit_course_update(request, c, request.POST)
    return edit_course_render(request, c)


@transaction.atomic
def edit_course_update(request, course_code, new_details):
    """Given the @new_details for @course_code, update
    these details in the database, and handle any updates
    needed with regards to enrolled users"""
    owner = request.user
    old_course = m.Course.objects.get(code=course_code)
    updated_form = f.CourseForm(new_details)
    if not updated_form.is_valid():
        raise Exception("validity problem")
    old_course.code = updated_form.cleaned_data['code']
    old_course.name = updated_form.cleaned_data['name']
    old_course.save()

    new_students = updated_form.cleaned_data['student'].strip().strip(',').split(',')
    new_students_list = list(map(lambda w: w.strip(), new_students))

    enrollments = m.EnrolledUser.objects.filter(course=old_course)
    for item in enrollments:
        if item.login == owner:
            continue
        if str(item.login) not in new_students_list:
            item.delete()
    for item in new_students_list:
        current_user = m.User.objects.get(username=item)
        exists = m.EnrolledUser.objects.filter(login=current_user).filter(course=old_course)
        if exists.count() != 1:
            new_item = m.EnrolledUser(login=current_user, course=old_course)
            new_item.save()


def edit_course_render(request, requested_course_code):
    """Get the details of @requested_course_code, coursework
    items and all the enrolled users and then
    populate the form before displaying it to user"""
    course = m.Course.objects.get(code=requested_course_code)
    enrollments = m.EnrolledUser.objects.select_related('login').filter(course=course)
    students = ""
    for eu in enrollments:
        students += str(eu.login) + ", "
    courseworks = m.Coursework.objects.filter(course=course)
    initial = {"code": course.code, "name": course.name, "student": students}
    update_form = f.CourseForm(initial)
    detail = {
        "course_name": course.name,
        "course_code": course.code,
        "courseworks": courseworks,
        "uf": update_form,
        "crumbs": [("Homepage", reverse("teacher_index"))]
    }
    return render(request, 'teacher/edit_course.html', detail)


@login_required()
@require_teacher
def create_coursework(request, c):
    """Handle form for creating a coursework in course @[c]"""
    cw = m.Course.objects.get(code=c)
    if not p.is_enrolled_on_course(request.user, cw):
        return HttpResponseForbidden("You are not enrolled on this course")
    if request.method == "POST":
        return create_coursework_update(request.user, request, c)
    return create_coursework_render(request, c)


def create_coursework_render(request, code):
    """Generate an empty form for creating a coursework for course @code"""
    detail = {
        "courseworks": {"name": "New Coursework"},
        "cw_form": f.CourseworkForm(),
        "creating": True,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   ("Course", reverse("edit_course", args=[code]))]
    }
    return render(request, 'teacher/edit_cw.html', detail)


@transaction.atomic
def create_coursework_update(user, request, course_code):
    """@user - Given the @request for a coursework, and
    the @course_code we want to add it to, update the db"""
    cw_form = f.CourseworkForm(request.POST)
    if not cw_form.is_valid():
        return HttpResponseBadRequest("Form contained invalid data. Please try again")
    course = m.Course.objects.get(code=course_code)
    coursework = m.Coursework(id=m.new_random_slug(m.Coursework),
                              course=course,
                              name=cw_form.cleaned_data['name'],
                              state=cw_form.cleaned_data['state'],
                              execute_script=cw_form.cleaned_data['execute_script'],
                              sol_path_re=cw_form.cleaned_data['sol_path_re'],
                              test_path_re=cw_form.cleaned_data['test_path_re'])
    coursework.save()

    descriptor = m.Submission(id=m.new_random_slug(m.Submission), coursework=coursework,
                              creator=user, type=m.SubmissionType.CW_DESCRIPTOR,
                              display_name="Coursework Descriptor")
    descriptor.save()
    for each in request.FILES.getlist('descriptor'):
        descriptor.save_uploaded_file(each)

    oracle_exec = m.Submission(id=m.new_random_slug(m.Submission), coursework=coursework,
                               creator=user, type=m.SubmissionType.ORACLE_EXECUTABLE,
                               display_name="Oracle Solution")
    oracle_exec.save()
    for each in request.FILES.getlist('oracle_exec'):
        oracle_exec.save_uploaded_file(each)

    sig = m.Submission(id=m.new_random_slug(m.Submission), coursework=coursework,
                       creator=user, type=m.SubmissionType.SIGNATURE_TEST,
                       display_name="Signature Test")
    sig.save()
    for each in request.FILES.getlist('signature'):
        sig.save_uploaded_file(each)

    return redirect(request, "Coursework created", reverse('edit_cw', args=[coursework.id]))


@login_required()
@require_teacher
def edit_coursework(request, c):
    """Prepare a page to view and edit coursework @[c]"""
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    if request.method == "POST":
        edit_coursework_update(request.POST, coursework)
    return edit_coursework_render(request, coursework)


@transaction.atomic()
def edit_coursework_update(new_details, old_coursework):
    """Given the @new_details, update the database for
    the details o @old_coursework"""
    updated_form = f.CourseworkForm(new_details)
    if not updated_form.is_valid():
        raise Exception("validity problem")
    old_coursework.name = updated_form.cleaned_data['name']
    old_coursework.state = updated_form.cleaned_data['state']
    old_coursework.execute_script = updated_form.cleaned_data['execute_script']
    old_coursework.sol_path_re = updated_form.cleaned_data['sol_path_re']
    old_coursework.test_path_re = updated_form.cleaned_data['test_path_re']
    old_coursework.save()


def edit_coursework_render(request, coursework):
    """Get all of the necessary details to display a
    page for a given @coursework, including the
    files uploaded for it, test data instances and
    of course the metadata about the coursework itself"""
    desc_types = [m.SubmissionType.CW_DESCRIPTOR, m.SubmissionType.ORACLE_EXECUTABLE,
                  m.SubmissionType.SIGNATURE_TEST]
    submissions = [(s, s.get_files()) for s in m.Submission.objects.filter(
        coursework=coursework, type__in=desc_types)]
    initial = {"name": coursework.name,
               "state": coursework.state,
               "execute_script": coursework.execute_script,
               "sol_path_re": coursework.sol_path_re,
               "test_path_re": coursework.test_path_re}
    cw_form = f.CourseworkForm(initial)
    detail = {
        "coursework": coursework,
        "cw_form": cw_form,
        "creating": False,
        "submissions": submissions,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   ("Course", reverse("edit_course", args=[coursework.course.code]))]
    }
    return render(request, 'teacher/edit_cw.html', detail)


@login_required()
@require_teacher
def edit_coursework_groups(request, c):
    """A teacher has made a @request to view the groups for
    coursework with @[c]. display the group edit forms"""
    fenrol.add_all_students_to_feedback_groups()
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    tm_initial = {"coursework": coursework.id}
    base_ff_form = ff.FeedbackGroupForm(tm_initial)
    extra_ff_forms = [ff.FeedbackGroupForm(initial) for
                      initial in ff.get_feedback_groups_as_iterable_forms(coursework)]
    detail = {
        "coursework": coursework,
        "feedback_form": base_ff_form,
        "feedback_forms": extra_ff_forms,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   (coursework.course.code, reverse("edit_course", args=[coursework.course.code])),
                   (coursework.name, reverse('edit_cw', args=[coursework.id]))]
    }
    return render(request, 'teacher/edit_groups.html', detail)

@login_required()
@require_teacher
def view_coursework_files(request, c):
    """A teacher has made a @request to view the file
    for coursework @[c]"""
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    # get all relevant submisions, as well as the creator because we need it later
    all_submissions = m.Submission.objects.filter(coursework=coursework).exclude(type=m.SubmissionType.TEST_RESULT).select_related(
        'creator','coursework','coursework__course'
    )
    submissions = [(s, s.get_time_for_version(), s.get_files()) for s in all_submissions.iterator()]
    tm_form = generate_teacher_easy_match_form(coursework)
    # string templates are faster than django templates
    rowTemplate = Template("""<tr>
    <td>$sid</td>
    <td>$type</type>
    <td>$creator</td>
    <td>$time</td>
    <td>$name (v$ver)</td>
    <td>$fileLinks</td>
</tr>""")
    fileTemplate = Template("<a href='$url'>$name</a><br/>")
    urlTemplate = reverse("download_file", kwargs={'sub_id': '_ID', 'filename': '_NAME'})
    response = ""
    for sub, time, files in submissions:
        fileLinks = ""
        suburl = urlTemplate.replace('_ID', sub.id)
        for f in files:
            thisUrl = suburl.replace('_NAME', f)+"?show=1"
            fileLinks += fileTemplate.substitute(url=thisUrl, name=f)
        response += rowTemplate.substitute(
            sid=sub.id,
            time=sub.get_time_for_version(),
            type=sub.type,
            creator=sub.creator,
            name=sub.display_name,
            ver=sub.latest_version,
            fileLinks=fileLinks
        )
    detail = {
        "coursework": coursework,
        "submissions": response,
        "tm_form": tm_form,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   (coursework.course.code, reverse("edit_course", args=[coursework.course.code])),
                   (coursework.name, reverse('edit_cw', args=[coursework.id]))]

    }
    return render(request, 'teacher/view_files.html', detail)

@login_required()
@require_teacher
def view_coursework_tms(request, c):
    """A teacher has made a @request to view the test matches
    for coursework @[c]. offer CSV if ?csv in GET request"""
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    # Get all related objects in one query
    results = m.TestMatch.objects.select_related(
        'test__creator',
        'solution__creator',).filter(coursework=coursework)
    # built reversed URLs for links with string concat rather than calling method repeatedly
    tm_url = reverse("tm", kwargs={"test_match_id": '', "commented": ''})
    # get all of the comments for all test matches and group them and count them
    with connection.cursor() as cursor:
        cursor.execute('SELECT object_pk, count(object_pk) FROM django_comments GROUP BY object_pk')
        comment_counts = {tm[0]: str(tm[1]) for tm in cursor.fetchall()}
    # build each row in the table
    if 'csv' in request.GET:
        response = "id,time,tester,test,testver,developer,solution,solutionver,commentcount,errorlevel,type\n"
        rowTemplate = Template("$tmid,$tmtime,$tester,$testname,$testver,$developer,$solname,$solver,$comments,$errorlevel,$type\n")
    else:
        response = ""
        rowTemplate = Template("""<tr>
            <td><a href="$tmurl">$tmid</a></td>
            <td>$tmtime</td>
            <td>$tester $testname $testver</td>
            <td>$developer $solname $solver</td>
            <td>$comments Comments</td>
            <td>$errorlevel</td>
            <td>$type</td>
            </tr>""")
    # its faster to build the string in python than in the django template
    for r in results.iterator():
        has_test = r.test is not None
        has_sol = r.solution is not None
        comment_count = comment_counts[r.id] if r.id in comment_counts else "0"
        response += rowTemplate.substitute(
            tmurl=tm_url + r.id,
            tmid=r.id,
            tmtime=str(r.timestamp),
            tester=r.test.creator.username if has_test else "",
            testname=r.test.display_name if has_test else "",
            testver="v"+str(r.test_version) if has_test else "",
            developer=r.solution.creator.username if has_sol else "",
            solname=r.solution.display_name if has_sol else "",
            solver="v"+str(r.solution_version) if has_sol else "",
            comments=comment_count,
            errorlevel="Success" if r.error_level==0 else "E"+str(r.error_level) if r.error_level is not None else "Queued",
            type=r.type
        )
    # now pass everything to the renderer
    if 'csv' in request.GET:
        httpresponse = HttpResponse(content_type='text/csv')
        httpresponse['Content-Disposition'] = 'attachment; filename="somefilename.csv"'
        httpresponse.write(response)
        return httpresponse
    detail = {
        "coursework": coursework,
        "results": response,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   (coursework.course.code, reverse("edit_course", args=[coursework.course.code])),
                   (coursework.name, reverse('edit_cw', args=[coursework.id]))]
    }
    return render(request, 'teacher/view_tms.html', detail)

@login_required()
@require_teacher
def view_coursework_comments(request, c):
    """A teacher has made a @request to view the comments of coursework
    with @[c]. display files, tests"""
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    # get all comments, all test matches for current cw
    all_comments = cm.Comment.objects.select_related('user').all()
    tms_for_cw = m.TestMatch.objects.filter(coursework=coursework)
    # only pick comments that appeared on this coursework
    comment_list = [(c.submit_date, c.comment, c.user, c.object_pk)
                    for c in all_comments.iterator() if tms_for_cw.filter(id=c.object_pk).exists]
    # string templates faster than django templates
    response = ""
    commentTemplate = Template("""<div class="comment">
    <h4>$user on $date in <a href="$link">$content_object</a></h4>
    <p>$comment</p>
</div>""")
    tm_url = reverse("tm", kwargs={"test_match_id": '', "commented": ''})
    for comment in comment_list:
        response += commentTemplate.substitute(
            user=str(comment[2]),
            date=str(comment[0]),
            link=tm_url+comment[3],
            content_object=comment[3],
            comment=comment[1]
        )
    detail = {
        "coursework": coursework,
        "comment_list": response,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   (coursework.course.code, reverse("edit_course", args=[coursework.course.code])),
                   (coursework.name, reverse('edit_cw', args=[coursework.id]))]
    }
    return render(request, 'teacher/view_cw_comments.html', detail)


def generate_teacher_easy_match_form(coursework, post=None):
    """Given an instance of @coursework, generate a
    relevant easymatchform"""
    tests = [(t.id, t.teacher_display_name()) for t in m.Submission.objects.select_related('creator').filter(
        coursework=coursework,
        type__in=[m.SubmissionType.TEST_CASE, m.SubmissionType.SIGNATURE_TEST])]
    solutions = [(s.id, s.teacher_display_name()) for s in m.Submission.objects.select_related('creator').filter(
        coursework=coursework,
        type__in=[m.SubmissionType.SOLUTION, m.SubmissionType.ORACLE_EXECUTABLE])]
    # sort by name not id
    tests.sort(key=lambda x:x[1])
    solutions.sort(key=lambda x:x[1])
    if post is None:
        return cf.EasyMatchForm(tests, solutions)
    return cf.EasyMatchForm(tests, solutions, post)


@login_required()
@require_teacher
def create_test_match(request, c):
    """Create a new test match, according to what is specified in the POST request"""
    coursework = m.Coursework.objects.get(id=c)
    if not request.POST:
        return HttpResponseForbidden("You're supposed to POST a form here")
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You're not enrolled on this course")
    return manual_test_match_update(request, coursework)


def manual_test_match_update(request, coursework):
    """Create a new test match with data specified in @request for @coursework"""
    tm_form = generate_teacher_easy_match_form(coursework, request.POST)
    if not tm_form.is_valid():
        return HttpResponseBadRequest("Invalid form data")
    try:
        new_tm = matcher.create_teacher_test(
            tm_form.cleaned_data['solution'],
            tm_form.cleaned_data['test'],
            coursework
        )
        r.run_test_on_thread(new_tm)
    except Exception as e:
        return HttpResponseBadRequest(str(e))
    return redirect(request, "Test created",
                    reverse('view_cw_tms', args=[coursework.id]))


@login_required()
@require_teacher
def run_all_test_in_cw(request, c):
    """Run all of the queued tests for coursework with id @c"""
    cw = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, cw.course):
        return HttpResponseForbidden("you're not enrolled on this course")
    r.run_queued_tests_on_thread(cw)
    return redirect(request, "Starting to run queued tests", reverse('view_cw_tms', args=[cw.id]))


@login_required()
@require_teacher
@transaction.atomic()
def update_content(request):
    if request.method != "POST":
        return HttpResponseForbidden("You are only allowed to POST here")
    old_sub = m.Submission.objects.get(id=request.POST['old_id'])
    if not p.is_enrolled_on_course(request.user, old_sub.coursework.course):
        return HttpResponseForbidden("you're not enrolled on this course")

    old_sub.increment_version()
    for each in request.FILES.getlist('new_content'):
        old_sub.save_uploaded_file(each)

    return redirect(request, "Content Updated", reverse('edit_cw', args=[old_sub.coursework.id]))


@login_required()
@require_teacher
def view_timeline(request, c, s):
    """A teacher has made a @request to view the timeline
    of events for @s student id in @cw"""
    coursework = m.Coursework.objects.get(id=c)
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You are not enrolled on this course")
    student = m.User.objects.get(username=s)
    if not p.is_enrolled_on_course(student, coursework.course):
        return HttpResponseForbidden("Student is not enrolled on this course")
    events = []
    # get commits
    submissions = m.Submission.objects.select_related('coursework',
     'coursework__course').filter(creator=student, coursework=coursework,
      type__in=[m.SubmissionType.TEST_CASE, m.SubmissionType.SOLUTION])
    for submission in submissions.iterator():
        versions = submission.latest_version
        for i in range(0, submission.latest_version):
            date = submission.get_time_for_version(i).astimezone(tz=None)
            name = 'Submitted ' + submission.display_name
            desc = str(submission)
            events.append((date, name, desc))
    all_tms = m.TestMatch.objects.select_related('test', 'solution').filter(coursework=coursework)
    all_comments = cm.Comment.objects.filter(user=student)
    # just get comments for this coursework's tms
    comment_list = [c for c in all_comments.iterator() if all_tms.filter(id=c.object_pk).exists]
    for tm in all_tms.iterator():
        if tm.type == m.TestType.SELF:
            date = tm.timestamp.astimezone(tz=None)
            name = 'Created Self-Test'
            desc = 'Solution version: ' + str(tm.solution_version) + ', Test version: ' + str(tm.test_version)
        elif tm.test.creator_id == student.id:
            date = tm.timestamp.astimezone(tz=None)
            name = 'Created Test Match with ' + tm.solution.creator.username
            desc = str(tm)
            events.append((date, name, desc))
        elif tm.test.creator_id == student.id:
            date = tm.timestamp.astimezone(tz=None)
            name = 'Had Test Match created by ' + tm.test.creator.username
            desc = str(tm)
            events.append((date, name, desc))
    for comment in comment_list:
        date = comment.submit_date.astimezone(tz=None)
        name = 'Commented on Test Match'
        desc = comment.object_pk + comment.comment
        events.append((date, name, desc))
    events.sort(key=lambda x:x[0])
    detail = {
        "student_name": student.username,
        "events": events,
        "crumbs": [("Homepage", reverse("teacher_index")),
                   (coursework.course.code, reverse("edit_course", args=[coursework.course.code])),
                   (coursework.name, reverse('edit_cw', args=[coursework.id]))]
    }
    return render(request, 'teacher/timeline.html', detail)
