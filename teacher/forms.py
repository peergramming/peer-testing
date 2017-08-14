import django.forms as f

import common.models as m


# noinspection PyClassHasNoInit
class CourseForm(f.Form):
    code = f.SlugField(label="Course Code", max_length=32)
    name = f.CharField(max_length=128, label="Course Name")
    student = f.CharField(widget=f.Textarea, label="Comma-Separated Enrolled Users")


# noinspection PyClassHasNoInit
class CourseworkForm(f.Form):
    name = f.CharField(label="Coursework Name", max_length=128)
    state = f.ChoiceField(label="Coursework State", choices=m.CourseworkState.POSSIBLE_STATES)
    test_class = f.CharField(label="Test Class Name", max_length=128, required=False)
    runtime = f.ChoiceField(label="Runtime", choices=m.CourseworkRuntimes.POSSIBLE_RUNTIMES)


# noinspection PyClassHasNoInit
class AutoTestMatchForm(f.Form):
    algorithm = f.ChoiceField(label="Choice of Match Algorithm", choices=[])
    assign_markers = f.BooleanField(label="Assign Markers", required=False)
    visible_to_developer = f.BooleanField(label="Visible to developer", required=False)
