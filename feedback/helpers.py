from django.core.exceptions import ObjectDoesNotExist

import common.models as cm
import feedback.models as fm
from common.permissions import is_teacher


def nick_for_comment(user, group, requesting_user):
    """Find the nickname, for the specified @user in
     feedback @group, and customize appropriate to
     the status and relationship to @requesting_user.
     For use in comment section anon usernames"""
    try:
        if requesting_user == user:
            return "Me"
        if is_teacher(requesting_user):
            return user.username
        return fm.FeedbackMembership.objects.get(group=group, user=user).nickname
    except ObjectDoesNotExist:
        return "Unknown User - %s, %s" % user.id, group.id


def nick_for_display(group, requesting_user, submission, version):
    """Find the nickname, for the specified @user in
     feedback @group, and customize appropriate to
     the status and relationship to @requesting_user.
     For use in preparing display name of @submission"""
    try:
        if requesting_user == submission.creator:
            return "My %s%s" % (submission.display_name, " (v" + str(version) + ")" if submission.type == cm.SubmissionType.SOLUTION else "")
        if is_teacher(requesting_user):
            return "%s %s%s" % (submission.creator.username, submission.display_name, " (v" + str(version) + ")" if submission.type == cm.SubmissionType.SOLUTION else "")
        if is_teacher(submission.creator):
            return submission.display_name
        nick = fm.FeedbackMembership.objects.get(group=group, user=submission.creator).nickname
        return "%s %s%s" % (nick, submission.display_name, " (v" + str(version) + ")" if submission.type == cm.SubmissionType.SOLUTION else "")
    except ObjectDoesNotExist:
        return "Unknown User - %s, %s" % requesting_user.id, group.id


def get_feedback_groups_for_user_in_coursework(user, coursework):
    """Given @user trying to give feedback for @coursework
    get all of the groups they are assigned to as a list"""
    return [mb.group for mb in fm.FeedbackMembership.objects.filter(user=user)
            if mb.group.coursework == coursework]


def get_all_users_in_feedback_group(group):
    """Given a feedback @group, determine all of the member users"""
    return [(member.user, member.nickname) for member in
            fm.FeedbackMembership.objects.filter(group=group)]


def get_all_test_matches_in_feedback_group(user, group):
    """"Given a feedback @group,
    get all of the associated test matches
    that @user should be able to access"""
    return [detail_test_match_anon_names(user, tac.test, tac.group) for tac in
            fm.TestAccessControl.objects.filter(group=group) if
            tac.initiator == user or tac.test.solution.creator == user]


def detail_test_match_anon_names(user, tm, group=None):
    """Given a instance of a @user, a @tm and a
    feedback @group, get the details of names of
    the submission within the @tm as a tuple
    (test match, solution name, test name)"""
    if group is None:
        return tm, tm.solution.display_name, tm.test.display_name
    group_query = fm.TestAccessControl.objects.filter(test=tm)
    if not group_query.exists():
        return tm, tm.solution.display_name, tm.test.display_name
    else:
        group = group_query.first().group
    sol_name = nick_for_display(group, user, tm.solution, tm.solution_version)
    test_name = nick_for_display(group, user, tm.test, tm.test_version)
    return tm, sol_name, test_name

def get_peer_user_in_test_match(user, tm):
    """Given a instance of a @user and a @tm,
    get the peer user for notification"""
    test_user = tm.test.creator
    sol_user = tm.solution.creator
    if user == test_user and user == sol_user:
        return None
    elif user != test_user and user != sol_user:
        return None
    elif user != test_user:
        return test_user
    elif user != sol_user:
        return sol_user
    else:
        return None

def count_members_of_group(group):
    """Count the number of members of specified feedback @group"""
    return fm.FeedbackMembership.objects.filter(group=group).count()


def feedback_group_for_test_match(tm):
    """Given a @tm, get the feedback group associated"""
    grouping = fm.TestAccessControl.objects.filter(test=tm)
    return grouping.first().group if grouping.exists() else None


def user_is_member_of_group(user, group_id):
    """Given a @user and a @group_id, determine if membership exists"""
    group = fm.FeedbackGroup.objects.get(id=group_id)
    return fm.FeedbackMembership.objects.filter(group=group, user=user).exists()
