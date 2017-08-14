import os
import random
import shutil
import string

from django.contrib.auth.models import User
from django.db import models as m
from django.conf import settings


slug_characters = ['-', '_'] + list(string.ascii_letters) + list(string.digits)


def new_random_slug(model, primary_key='id', length=8):
    """For a given @model, find a new random slug of @length
    which is unique against the primary key of the model. can
    specify a @primary_key if it is different to 'id'"""
    exists = True
    new_slug = ""
    while exists:
        new_slug = ""
        for count in range(length):
            new_slug += random.choice(slug_characters)
        exists = model.objects.filter(**{primary_key: new_slug}).count() > 0
    return new_slug


# noinspection PyClassHasNoInit
class Course(m.Model):
    name = m.CharField(max_length=128)
    code = m.SlugField(max_length=32, primary_key=True)

    def __str__(self):
        return self.name


# noinspection PyClassHasNoInit
class EnrolledUser(m.Model):
    class Meta:
        unique_together = (('login', 'course'),)

    login = m.ForeignKey(User, m.CASCADE)
    course = m.ForeignKey(Course, m.CASCADE)

    def __str__(self):
        return str(self.course) + ", " + str(self.login)


class CourseworkState:
    INVISIBLE = 'i'
    CLOSED = 'c'
    UPLOAD = 'u'
    FEEDBACK = 'f'
    POSSIBLE_STATES = (
        (INVISIBLE, 'Invisible to Students'),
        (CLOSED, 'Closed for Submissions'),
        (UPLOAD, 'Self-Testing and Solutions'),
        (FEEDBACK, 'Peer-Testing and Feedback'),
    )


class CourseworkRuntimes:
    NOEXEC = ''
    PYTHON3 = 'p3'
    JAVA8 = 'j8'
    POSSIBLE_RUNTIMES = (
        (NOEXEC, 'No Execution'),
        (PYTHON3, 'Python 3'),
        (JAVA8, 'Java 8')
    )


# noinspection PyClassHasNoInit
class Coursework(m.Model):
    id = m.SlugField(max_length=8, primary_key=True)
    name = m.CharField(max_length=128)
    course = m.ForeignKey(Course, m.CASCADE)
    state = m.CharField(max_length=1,
                        choices=CourseworkState.POSSIBLE_STATES,
                        default=CourseworkState.INVISIBLE)
    runtime = m.CharField(max_length=8,
                          choices=CourseworkRuntimes.POSSIBLE_RUNTIMES,
                          default=CourseworkRuntimes.NOEXEC)
    test_class = m.CharField(max_length=128)

    def is_visible(self):
        """Show if the coursework state allows it to be visible"""
        return self.state != CourseworkState.INVISIBLE

    def __str__(self):
        return self.name


class SubmissionType:
    SOLUTION = 's'
    TEST_CASE = 'c'
    TEST_RESULT = 'r'
    CW_DESCRIPTOR = 'd'
    ORACLE_EXECUTABLE = 'e'
    SIGNATURE_TEST = 'i'
    POSSIBLE_TYPES = (
        (SOLUTION, 'Solution to Coursework'),
        (TEST_CASE, 'Test Case for Solution'),
        (TEST_RESULT, 'Results of Running Test Case'),
        (CW_DESCRIPTOR, 'Coursework Task Descriptor, sample files'),
        (ORACLE_EXECUTABLE, 'Executable that tests run against that gives expected output'),
        (SIGNATURE_TEST, 'Test solution matches signature, interface, compiles, etc.'),
    )


# noinspection PyClassHasNoInit
class Submission(m.Model):
    id = m.SlugField(max_length=8, primary_key=True)
    coursework = m.ForeignKey(Coursework, m.CASCADE)
    creator = m.ForeignKey(User, m.CASCADE)
    type = m.CharField(max_length=1, choices=SubmissionType.POSSIBLE_TYPES)
    display_name = m.CharField(max_length=64, null=True)
    latest_version = m.IntegerField(default=0)

    def __str__(self):
        return str(self.coursework) + " - " + self.display_name

    def path(self):
        """Give path where submission is stored"""
        if self.type in [SubmissionType.CW_DESCRIPTOR, SubmissionType.ORACLE_EXECUTABLE,
                         SubmissionType.SIGNATURE_TEST]:
            return os.path.join(settings.BASE_DIR,
                                settings.MEDIA_ROOT,
                                str(self.coursework.course.name),
                                str(self.coursework.name),
                                "descriptors",
                                self.display_name,
                                self.id)
        if self.type == SubmissionType.TEST_RESULT:
            return os.path.join(settings.BASE_DIR,
                                settings.MEDIA_ROOT,
                                str(self.coursework.course.name),
                                str(self.coursework.name),
                                "runs",
                                self.id)
        return os.path.join(settings.BASE_DIR,
                            settings.MEDIA_ROOT,
                            str(self.coursework.course.name),
                            str(self.coursework.name),
                            "students",
                            str(self.creator),
                            self.display_name,
                            self.id)

    def originals_path(self, version=None):
        """Give the path where the original files
        (unprocessed) that were uploaded are stored"""
        if version is None:
            version = self.latest_version
        return os.path.join(self.path(), str(version))

    def get_files(self, version=None):
        """Get the names of original files for
        this submission, without full path"""
        if version is None:
            version = self.latest_version
        return [file for file in os.listdir(self.originals_path(version))]

    def increment_version(self):
        """before any new versions of files are
        added, this method should be called"""
        self.latest_version += 1
        self.save()

    def save_content_file(self, content, name):
        """Given the @content string for a new file
        with @name, store it in the current submission"""
        path = os.path.join(self.originals_path(), name)
        os.makedirs(self.originals_path(), exist_ok=True)
        with open(path, "x") as file:
            file.write(content)

    def save_uploaded_file(self, file):
        """Given a @file a user has uploaded, store
        it in the current submission with @name"""
        path = os.path.join(self.originals_path(), file.name)
        os.makedirs(self.originals_path(), exist_ok=True)
        with open(path, "xb") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

    def delete(self, *args, **kargs):
        """Delete all of the files associated with this
        submission, by rm-ing the directory"""
        shutil.rmtree(self.path())
        super(Submission, self).delete(*args, **kargs)


class TestType:
    SELF = 's'
    PEER = 'p'
    TEACHER = 't'
    POSSIBLE_TYPES = (
        (SELF, 'A Self-Test, the developer of the solution testing their own code'),
        (PEER, 'A Peer-Test, the tester is testing someone else\'s code'),
        (TEACHER, 'A teacher wants to test the code of a student')
    )


# noinspection PyClassHasNoInit
class TestMatch(m.Model):
    id = m.SlugField(max_length=8, primary_key=True)
    test = m.ForeignKey(Submission, m.CASCADE, related_name="tm_test_sub")
    test_version = m.IntegerField()
    solution = m.ForeignKey(Submission, m.CASCADE, related_name="tm_sol_sub")
    solution_version = m.IntegerField()
    result = m.ForeignKey(Submission, m.CASCADE, null=True, related_name="tm_res_sub")
    error_level = m.IntegerField(null=True)
    coursework = m.ForeignKey(Coursework, m.CASCADE, related_name="tm_cw")
    type = m.CharField(max_length=1, choices=SubmissionType.POSSIBLE_TYPES)

    def __str__(self):
        return str(self.coursework) + " - " + self.id

    def has_been_run(self):
        """return bool as to whether or not this test
        match has been run (successfully or not)"""
        return self.error_level is not None

    @staticmethod
    def test_match_for_results(results_submission):
        """Given that a @results_submission only is ever 
        attached to a single test match, retrieve it"""
        return TestMatch.objects.get(result=results_submission)
