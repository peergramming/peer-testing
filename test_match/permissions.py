
from enum import Enum
import common.permissions as p
from feedback.models import TestAccessControl as tac
from common.models import CourseworkState


class TestMatchMode(Enum):
    """Enumerate possible actions a user has with regards
    to viewing a test match instance and writing feedback."""
    DENY = 0
    READ = 1
    WRITE = 2
    WAIT = 3


def user_feedback_mode(user, test_match_instance):
    """Return the status that the @user has in relation
    to a particular @test_match_instance wrt feedback"""
    cw = test_match_instance.coursework
    if not p.can_view_coursework(user, cw):
        return TestMatchMode.DENY
    if p.is_teacher(user):
        # Would se this to READ so that teacher do not comment
        # but WRITE needed to demo with teacher account
        #return TestMatchMode.READ
        return TestMatchMode.WRITE
    if p.user_is_self_testing(user, test_match_instance):
        return state_given_error_level(test_match_instance, TestMatchMode.READ)
    if tac.user_has_test_access(user, test_match_instance):
        mode = feedback_mode_given_coursework_state(test_match_instance)
        return state_given_error_level(test_match_instance, mode)
    return TestMatchMode.DENY


def state_given_error_level(test_match_instance, specified_mode):
    """Assuming a user is properly validated and
    allowed to see a @test_match_instance, determine if
    they should be in WAIT or @specified_mode"""
    if test_match_instance.error_level is None:
        return TestMatchMode.WAIT
    return specified_mode


def feedback_mode_given_coursework_state(test_match_instance):
    """Based on the current state of the coursework, determine if
    authorized users should be allowed to write feedback"""
    if test_match_instance.coursework.state == CourseworkState.FEEDBACK:
        return TestMatchMode.WRITE
    return TestMatchMode.READ
