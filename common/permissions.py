
import common.models as m
from django.http import HttpResponseForbidden, Http404


def require_teacher(f):
    """Mixin to prevent pages from being viewed if the
    currently logged in user is not in the teacher group.
    Passes rest of args on as a dictionary"""

    def is_teacher_internal(request, **args):
        if is_teacher(request.user):
            if not args:
                return f(request)
            return f(request, **args)
        return HttpResponseForbidden("You must be a teacher to view this page")

    return is_teacher_internal


def coursework_access(f):
    """Mixin to ensure a coursework defined by id @cw exists,
    and that the user in @request has the rights to see it"""

    def coursework_access_internal(request, cw, **args):
        cw_instance = m.Coursework.objects.filter(id=cw).first()
        if cw_instance is None:
            return Http404("No coursework has been specified, or coursework does not exist")
        if not can_view_coursework(request.user, cw_instance):
            return HttpResponseForbidden("You are not allowed to see this coursework")
        return f(request, cw_instance, **args)

    return coursework_access_internal


def is_teacher(user):
    """is @user a teacher?"""
    return user.groups.filter(name='teacher').exists()


def is_owner_of_solution(user, test_match_instance):
    """For a given @user, are they the owner of the solution
    in the @test_match_instance"""
    return test_match_instance.solution.creator == user


def can_view_coursework(user, coursework):
    """BOOL: Check if the given @user instance is
    allowed to view the specified @coursework instance"""
    is_enrolled = m.EnrolledUser.objects.filter(login=user, course=coursework.course)
    if not is_enrolled.exists():
        return False
    return True if is_teacher(user) else coursework.is_visible()


def is_enrolled_on_course(user, course):
    """Determine if @user is enrolled on @course"""
    return m.EnrolledUser.objects.filter(login=user, course=course).exists()


def user_is_self_testing(user, test_match_instance):
    """Check and return whether @user was involved in a
    self-test for @test_match_instance. OR, if the user
    did not start the test_match_instance, determine if
    it could appear as a self-test"""
    if test_match_instance.type != m.TestType.SELF:
        return False
    return test_match_instance.test.creator == user or test_match_instance.solution.creator == user


def submission_is_descriptive(submission):
    """Report if a @submission is a descriptive part of
    a coursework"""
    return submission.type in [m.SubmissionType.CW_DESCRIPTOR, m.SubmissionType.SIGNATURE_TEST]


def submission_is_secret(submission):
    """Report is a @submission is the kind that ought to be secret
    to students taking part in coursework"""
    return submission.type == m.SubmissionType.ORACLE_EXECUTABLE


def user_owns_submission(user, submission):
    """Return if @user is the owner of @submission,
    for example if they are the creator"""
    return user == submission.creator
