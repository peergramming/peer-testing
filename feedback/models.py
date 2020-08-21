from django.contrib.auth.models import User
from django.db import models as m

import common.models as sm


# noinspection PyClassHasNoInit
class FeedbackGroup(m.Model):
    coursework = m.ForeignKey(sm.Coursework, on_delete=m.CASCADE)
    
    def __str__(self):
        return str(self.coursework) + " - " + str(self.id)


# noinspection PyClassHasNoInit
class FeedbackMembership(m.Model):
    class Meta:
        unique_together = (('group', 'user',),
                           ('group', 'nickname'))

    group = m.ForeignKey(FeedbackGroup, on_delete=m.CASCADE)
    user = m.ForeignKey(User, on_delete=m.CASCADE)
    nickname = m.CharField(max_length=32)

    def __str__(self):
        return "g%s - %s (%s)" % (self.group, self.user, self.nickname)

class TestAccessControl(m.Model):
    test = m.ForeignKey(sm.TestMatch, on_delete=m.CASCADE)
    initiator = m.ForeignKey(User, on_delete=m.CASCADE)
    group = m.ForeignKey(FeedbackGroup, on_delete=m.CASCADE)

    def __str__(self):
        return "%s - %s, %s" % (self.test, self.initiator, self.group)

    @staticmethod
    def user_has_test_access(user, test_match_instance):
        """Return whether or not a user is a member of the
        feedback group for a given test match"""
        tacs = TestAccessControl.objects.filter(test=test_match_instance)
        if not tacs.exists():
            return False
        tac = tacs.first()
        group_membership = FeedbackMembership.objects.filter(group=tac.group, user=user)
        return group_membership.exists() and ( tac.initiator == user or
               tac.test.solution.creator == user )
    
    @staticmethod
    def user_has_submission_access(user, submission, test_context):
        """Determine whether @user has sufficient permission
        to view @submission - i.e. they are in the group and
        have created the (test,sub version) @test_context using the submission"""
        if user == submission.creator:
            return True
        tests = sm.TestMatch.objects.filter(id=test_context[0])
        if not tests.exists():
            return False
        test = tests.first()
        ver = test_context[1]
        tacs = TestAccessControl.objects.filter(test=test)
        if not tacs.exists():
            return False
        tac = tacs.first()
        return ((tac.test.solution == submission and tac.test.solution_version == ver) or
                (tac.test.test == submission and tac.test.test_version == ver) or
                tac.test.result == submission) and \
                TestAccessControl.user_has_test_access(user, tac.test)
