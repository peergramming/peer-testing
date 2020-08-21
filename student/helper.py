"""A selection of methods that offer help to some other
functionality of the program, but in and of themselves
do not actually offer services to views, permissions etc."""

import common.models as m
import common.permissions as p


def coursework_available_for_user(user):
    """For a given @request, return a list of coursework available to the user"""
    enrolled_courses = m.EnrolledUser.objects.filter(login=user).values('course')
    courses_for_user = m.Course.objects.filter(code__in=enrolled_courses)
    all_courseworks_for_user = m.Coursework.objects.filter(course__in=courses_for_user)
    visible_courseworks = []
    for item in all_courseworks_for_user:
        if p.can_view_coursework(user, item):
            visible_courseworks.append((item.id, item.state, item.course.code, item.name))
    return visible_courseworks


def user_can_upload_of_type(user, coursework, up_type):
    """For a given @user, within the scope of a @coursework,
    determine whether or not they are allowed to upload an @up_type file"""
    if not p.can_view_coursework(user, coursework):
        return False
    if coursework.state == m.CourseworkState.UPLOAD:
        return up_type in [m.SubmissionType.SOLUTION, m.SubmissionType.TEST_CASE]
    if coursework.state == m.CourseworkState.FEEDBACK:
        return up_type in [m.SubmissionType.SOLUTION, m.SubmissionType.TEST_CASE]
    return False


def delete_old_solution(user, cw_instance):
    """For a given @cw_instance, and a @user, delete the existing
    solution file if it exists as it is about to be replaced.
    By itself, this method is NOT ATOMIC"""
    solution = m.Submission.objects.filter(creator=user, coursework=cw_instance,
                                           type=m.SubmissionType.SOLUTION)
    if solution.exists():
        solution.first().delete()


def delete_submission(user, submission):
    """Given a @user and a @submission, see if the user
    is allowed to delete said submission, and carry out"""
    if submission.creator != user:
        return False
    if can_delete(submission):
        submission.delete()
        return True
    return False


def can_delete(submission):
    """Assuming that the owner of the @submission is verified,
    check that it can actually be deleted safely"""
    return (submission.coursework.state in [m.CourseworkState.FEEDBACK, m.CourseworkState.UPLOAD]
            and submission.type == m.SubmissionType.TEST_CASE
            and m.TestMatch.objects.filter(test=submission).count() == 0)


def get_descriptor_tuples(coursework):
    """Get the descriptors and files for @coursework"""
    return [(s, s.get_files()) for s in m.Submission.objects.filter(
        type=m.SubmissionType.CW_DESCRIPTOR, coursework=coursework)]


def get_solution_tuples(coursework, user):
    """Get the solution submissions and files
    for @coursework by @user"""
    return [(s, s.get_files()) for s in
            m.Submission.objects.filter(coursework=coursework, creator=user,
                                        type=m.SubmissionType.SOLUTION)]


def get_test_triples(coursework, user):
    """Get the test submissions and files, and
    ability to delete for @coursework by @user"""
    return [(t, t.get_files(), can_delete(t)) for t in m.Submission.objects.filter(
        coursework=coursework, creator=user, type=m.SubmissionType.TEST_CASE)]
