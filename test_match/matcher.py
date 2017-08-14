from django.db import transaction

import common.models as m
import feedback.models as fm


@transaction.atomic()
def create_peer_test(solution, test, cw, feedback_group, initiator):
    """Create a new test match with data specified by the IDs of @solution,
    @test, @feedback_group and the instance of @cw, @initiator"""
    group = fm.FeedbackGroup.objects.get(id=feedback_group)
    solution = m.Submission.objects.get(id=solution, coursework=cw,
     type__in=[m.SubmissionType.ORACLE_EXECUTABLE, m.SubmissionType.SOLUTION])
    test_case = m.Submission.objects.get(id=test, coursework=cw,
     type__in=[m.SubmissionType.TEST_CASE, m.SubmissionType.SIGNATURE_TEST])
    if solution.type != m.SubmissionType.ORACLE_EXECUTABLE:
        if not fm.FeedbackMembership.objects.filter(group=group, user=solution.creator).exists():
            raise Exception("That solution is not included in your feedback group")
    if test_case.type != m.SubmissionType.SIGNATURE_TEST:
        if test_case.creator != initiator:
            raise Exception("You need to do peer testing with your own test")
    if solution.type == m.SubmissionType.ORACLE_EXECUTABLE and test_case.type == m.SubmissionType.SIGNATURE_TEST:
        raise Exception("Either test, solution or both need to be a student upload")
    new_tm = m.TestMatch(id=m.new_random_slug(m.TestMatch),
                         test=test_case,
                         test_version=test_case.latest_version,
                         solution=solution,
                         solution_version=solution.latest_version,
                         coursework=cw,
                         type=m.TestType.PEER)
    new_tm.save()
    fm.TestAccessControl(test=new_tm, group=group, initiator=initiator).save()
    return new_tm


@transaction.atomic()
def create_teacher_test(solution, test, cw):
    """Create a new test match with data specified by the IDs of @solution,
    @test, and @cw instanceand create the teachers test"""
    solution = m.Submission.objects.get(id=solution, coursework=cw,
     type__in=[m.SubmissionType.ORACLE_EXECUTABLE, m.SubmissionType.SOLUTION])
    test_case = m.Submission.objects.get(id=test, coursework=cw,
     type__in=[m.SubmissionType.TEST_CASE, m.SubmissionType.SIGNATURE_TEST])
    new_tm = m.TestMatch(id=m.new_random_slug(m.TestMatch),
                         test=test_case,
                         test_version=test_case.latest_version,
                         solution=solution,
                         solution_version=solution.latest_version,
                         coursework=cw,
                         type=m.TestType.TEACHER)
    new_tm.save()
    return new_tm


@transaction.atomic()
def create_self_test(solution, test, cw, initiator):
    """Receive data to create a student-specific test match. Pass in IDs for
    @solution, @test and a @cw, @initiator user instance. Return the newly created test."""
    solution = m.Submission.objects.get(id=solution, coursework=cw,
     type__in=[m.SubmissionType.ORACLE_EXECUTABLE, m.SubmissionType.SOLUTION])
    test_case = m.Submission.objects.get(id=test, coursework=cw,
     type__in=[m.SubmissionType.TEST_CASE, m.SubmissionType.SIGNATURE_TEST])
    if solution.type == m.SubmissionType.ORACLE_EXECUTABLE and test_case.type == m.SubmissionType.SIGNATURE_TEST:
        raise Exception("Either test, solution or both need to be a student upload")
    if solution.type != m.SubmissionType.ORACLE_EXECUTABLE:
        if solution.creator != initiator:
            raise Exception("You need to do self testing with your own solution")
    if test_case.type != m.SubmissionType.SIGNATURE_TEST:
        if test_case.creator != initiator:
            raise Exception("You need to do self testing with your own test")
    new_tm = m.TestMatch(id=m.new_random_slug(m.TestMatch),
                         test=test_case,
                         test_version=test_case.latest_version,
                         solution=solution,
                         solution_version=solution.latest_version,
                         coursework=cw,
                         type=m.TestType.SELF)
    new_tm.save()
    return new_tm


def create_self_test_for_new_solution(solution):
    """Given a newly created @solution instance,  run the
    appropriate signature test on it"""
    signature = m.Submission.objects.get(coursework=solution.coursework,
                                         type=m.SubmissionType.SIGNATURE_TEST)
    return create_self_test(solution.id, signature.id, solution.coursework, solution.creator)
