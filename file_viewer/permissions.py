
import common.permissions as p
from feedback.models import TestAccessControl
import common.models as m


def can_view_file(user, file, context=None):
    """Determine if a @user should be allowed to view a given @file"""
    return can_view_submission(user, file.submission, context)


def can_view_submission(user, submission, context=None):
    """Determine is a @user is allowed to see a given @submission
    Optionally specify a @context ID (e.g. test match)"""
    if not p.can_view_coursework(user, submission.coursework):
        return False
    if p.is_teacher(user):
        return True
    if p.submission_is_descriptive(submission):
        return True
    if p.submission_is_secret(submission):
        return False
    if p.user_owns_submission(user, submission):
        return True
    if TestAccessControl.user_has_submission_access(user, submission, context):
        return True
    if is_visible_results_file(user, submission):
        return True
    return False


def is_visible_results_file(user, submission):
    """If the @submisison that @user is trying to  view is a
    results file, find the test it is from. If it is a self
    test for @user, let them see it. If they are in the testing
    group, let them see it"""
    if submission.type != m.SubmissionType.TEST_RESULT:
        return False
    test_used_in = m.TestMatch.test_match_for_results(submission)
    return p.user_is_self_testing(user, test_used_in) or \
        TestAccessControl.user_has_test_access(user, test_used_in)
