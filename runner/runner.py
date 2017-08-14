import threading
from django.db import transaction
import common.models as m
import test_match.matcher as matcher
import runner.pyunit
import runner.junit
import runner.noexec
import os
from django.conf import settings


def get_correct_module(coursework):
    """Given a @courseowrk, determine which module should
    be used to run the test and processing"""
    if coursework.runtime == m.CourseworkRuntimes.PYTHON3:
        return runner.pyunit, ""
    if coursework.runtime == m.CourseworkRuntimes.JAVA8:
        return runner.junit, os.path.join(settings.BASE_DIR, "libs", "junit")
    if coursework.runtime == m.CourseworkRuntimes.NOEXEC:
        return runner.noexec, ""
    raise Exception("unknown test type")


def run_test_in_thread(test_match):
    """Look at the specified @test_match, acquire the relevant files for
    the testing to happen, and then determine which execution / testing
    module should be used ot test it and execute appropriately"""
    solutions = test_match.solution.get_files()
    sols_dir = test_match.solution.originals_path()
    test_dir = test_match.test.originals_path()
    test_class = test_match.coursework.test_class
    mod, libs = get_correct_module(test_match.coursework)
    error_level, result = mod.execute_test(sols_dir, test_dir, test_class, libs)
    update_test_match(error_level, result, test_match)


def run_test_on_thread(test_instance):
    """Start a new thread and run the @test_instance,
    if it hasnt already been run"""
    running = threading.Thread(target=run_test_in_thread, args=(test_instance,))
    running.start()


def run_queued_tests_in_thread(coursework):
    """go through all of the test data instances that are
    tagged as waiting to run for @coursework, and run them"""
    while True:
        tests = m.TestMatch.objects.filter(coursework=coursework, error_level=None)
        if tests.count() == 0:
            return
        for test in tests:
            run_test_in_thread(test)


def run_queued_tests_on_thread(coursework):
    """Run all queued test sin @coursework, but on a new thread"""
    running = threading.Thread(target=run_queued_tests_in_thread, args=(coursework,))
    running.start()


def run_signature_test(solution):
    """A new @solution submission has been created
    and we wish to run it against the appropriate
    signature test for that coursework"""
    # TODO may want separate method for testing compilation results?
    tm = matcher.create_self_test_for_new_solution(solution)
    run_test_on_thread(tm)


@transaction.atomic
def update_test_match(error_level, results, test_match):
    """update @test_match with the @results and
    the @error_level of running the tests"""
    result_submission = store_results(results, test_match)
    test_match.result = result_submission
    test_match.error_level = error_level
    test_match.save()


@transaction.atomic()
def store_results(content, tm):
    """Take in the @content from running a
    @tm test match instance, and save it,
    passing back a reference to submission"""
    result_sub = m.Submission(id=m.new_random_slug(m.Submission),
                              coursework=tm.coursework,
                              creator=tm.test.creator,
                              type=m.SubmissionType.TEST_RESULT,
                              display_name="Test Results")
    result_sub.save()
    result_sub.save_content_file(content, "results.txt")
    return result_sub
