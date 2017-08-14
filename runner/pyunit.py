import os
import re
import shutil
import subprocess
import tempfile


def prepare_temp_directory():
    """Create or clean up a temporary
    working directory at @path"""
    tmp_dir = tempfile.mkdtemp()
    init_dir = os.path.join(tmp_dir, '__init__.py')
    with open(init_dir, 'w+') as f:
        f.write('')
    return tmp_dir


def process_results(content):
    """Process @content of results of running test
    to clean up any unwanted information"""
    content2 = re.sub(r"(File [\"\']).+/(python[0-9.]+)/(.+[\"\'])", r"\1/\2/\3", content)
    return re.sub(r"(File [\"\']).+/var/tmp/(.+[\"\'])", r"\1/\2", content2)


def copy_all(paths, tmp_dir):
    """for list of at @path,
    copy them to @tmp_dir"""
    for file in os.listdir(paths):
        full_src_path = os.path.join(paths, file)
        if os.path.isfile(full_src_path):
            full_dst_path = os.path.join(tmp_dir, file)
            shutil.copy(full_src_path, full_dst_path)


def execute_test(path_solutions, path_tests, test_class, libs):
    """Given specific argument as to how to run the test,
    move all of the files into the correct directories and
    execute the test. 
    @path_solutions - path to where solution files located
    @path_tests - path to where testing files located
    @test_class - not used for python
    @libs - unused for python"""
    tmp_dir = prepare_temp_directory()
    copy_all(path_solutions, tmp_dir)
    copy_all(path_tests, tmp_dir)
    args = 'python3 -m unittest discover -p "*.py"'
    proc = subprocess.Popen(args, cwd=tmp_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
    outb, errb = proc.communicate()
    outs = "" if outb is None else outb.decode('utf-8')
    errs = "" if errb is None else errb.decode('utf-8')
    output = outs + errs
    cleaned_output = process_results(output)
    shutil.rmtree(tmp_dir)
    return proc.returncode, cleaned_output


def solution_uploaded(solutions):
    """a @solution is uploaded to specified directory.
    python does not require compilation so do nothing"""
    pass
