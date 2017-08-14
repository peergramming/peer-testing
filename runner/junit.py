import os
import shutil
import subprocess
import tempfile


def execute_test(path_solutions, path_tests, test_class, libs):
    """Given specific argument as to how to run the test,
    move all of the files into the correct directories and
    execute the test. 
    @path_solutions - path to where solution files located
    @path_tests - path to where testing files located
    @test_class - set by teacher, required by java,
       must be command-line safe (no cmd chars etc)
    @libs - location of libraries relevant to execution"""
    tmp_dir = tempfile.mkdtemp()
    copy_all(path_solutions, tmp_dir)
    copy_all(path_tests, tmp_dir)
    copy_all(libs, tmp_dir)
    comp_args = "javac -cp .:junit.jar *.java"
    compilation = subprocess.Popen(comp_args, cwd=tmp_dir,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True)
    outb, errb = compilation.communicate()
    if compilation.returncode != 0:
        outs = "" if outb is None else outb.decode('utf-8')
        errs = "" if errb is None else errb.decode('utf-8')
        output = "Failed to compile: \n" + outs + errs
        shutil.rmtree(tmp_dir)
        return compilation.returncode, output
    test_args = "java -cp .:junit.jar:hamcrest.jar org.junit.runner.JUnitCore " + test_class
    test = subprocess.Popen(test_args, cwd=tmp_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)
    outb, errb = test.communicate()
    outs = "" if outb is None else outb.decode('utf-8')
    errs = "" if errb is None else errb.decode('utf-8')
    output = outs + errs
    shutil.rmtree(tmp_dir)
    return test.returncode, output


def copy_all(paths, tmp_dir):
    """for list of at @path,
    copy them to @tmp_dir"""
    for file in os.listdir(paths):
        full_src_path = os.path.join(paths, file)
        if os.path.isfile(full_src_path):
            full_dst_path = os.path.join(tmp_dir, file)
            shutil.copy(full_src_path, full_dst_path)


def solution_uploaded(solution):
    """a @solution is uploaded, compile
     into relevant executable format"""
    pass
    # todo javac *.java
    # todo mv originals -> compiled


def test_uploaded(test):
    """a @test is uploaded, compile
    and reference junit jars"""
    pass
    # todo javac -cp .:junit.jar *.java
    # todo mv originals -> compiled


def process_results(content):
    """Process @content of results of running test
    to clean up any unwanted information"""
    return content
