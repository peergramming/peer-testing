import threading
from django.db import transaction
import common.models as m
import test_match.matcher as matcher
import os
import tempfile
import re
import shutil
import subprocess
from django.conf import settings


def execute_test(sols_dir, test_dir, execute_script):
    """Execute test
    @sols_dir - path to where solution files located
    @test_dir - path to where testing files located
    @execute_script - point to a file in lib dir that
       executes the test and any additional steps
       like compilation or editing"""
    tmp_dir = prepare_temp_directory()
    copy_all(sols_dir, tmp_dir)
    copy_all(test_dir, tmp_dir)
    lib_dir = os.path.join(settings.BASE_DIR, 'libs')
    args = [execute_script, tmp_dir, lib_dir]
    proc = subprocess.Popen(" ".join(args), cwd=tmp_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
    try:
        outb, errb = proc.communicate(timeout=30)
        code = proc.returncode
        output = process_output(outb, errb, 'Result')
    except subprocess.TimeoutExpired:
        proc.kill()
        output = process_output(outb,errb,"Time Out")
        code = 101
    except (OSError, subprocess.CalledProcessError) as exception:
        output = "Execution error: "+str(exception)
        code = 102
    finally:
        shutil.rmtree(tmp_dir)
        return proc.returncode, output

def prepare_temp_directory():
    """Create or clean up a temporary
    working directory at @path"""
    tmp_dir = tempfile.mkdtemp()
    init_dir = os.path.join(tmp_dir, '__init__.py')
    with open(init_dir, 'w+') as f:
        f.write('')
    return tmp_dir

def process_output(outb,errb,message):
    outs = "" if outb is None else outb.decode('utf-8')
    errs = "" if errb is None else errb.decode('utf-8')
    output = message + ": \n" + outs + errs
    return output

def copy_all(paths, tmp_dir):
    """for list of at @path,
    copy them to @tmp_dir"""
    for file in os.listdir(paths):
        full_src_path = os.path.join(paths, file)
        if os.path.isfile(full_src_path):
            full_dst_path = os.path.join(tmp_dir, file)
            shutil.copy(full_src_path, full_dst_path)

def run_test_in_thread(test_match):
    """Look at the specified @test_match, acquire the relevant files for
    the testing to happen, and then determine which execution / testing
    module should be used ot test it and execute appropriately"""
    solutions = test_match.solution.get_files()
    sols_dir = test_match.solution.originals_path()
    test_dir = test_match.test.originals_path()
    execute_script = test_match.coursework.execute_script
    if execute_script != '':
        fully_qualified_script = os.path.join(settings.BASE_DIR, 'libs', execute_script)
        error_level, result = execute_test(sols_dir, test_dir, fully_qualified_script)
        test_match.set_error_level(error_level)
        test_match.store_results(result)
    else:
        test_match.set_error_level(0)


def run_test_on_thread(test_instance):
    """Start a new thread and run the @test_instance,
    if it hasnt already been run"""
    running = threading.Thread(target=run_test_in_thread, args=(test_instance,))
    running.start()


def run_queued_tests_in_thread(coursework):
    """go through all of the test data instances that are
    tagged as waiting to run for @coursework, and run them"""
    while False:
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
    tm = matcher.create_self_test_for_new_solution(solution)
    run_test_on_thread(tm)
