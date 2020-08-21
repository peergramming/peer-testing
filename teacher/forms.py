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
    sol_path_re = f.CharField(label='Regular Expression indicating where to look for SOLUTION files when fetching from gitlab', max_length=256)
    test_path_re  = f.CharField(label='Regular Expression indicating where to look for TEST files when fetching from gitlab', max_length=256)
    execute_script = f.CharField(label='Name of script to use when executing a test. Leave blank if no compilation needed', max_length=64, required=False)


# noinspection PyClassHasNoInit
class AutoTestMatchForm(f.Form):
    algorithm = f.ChoiceField(label="Choice of Match Algorithm", choices=[])
    assign_markers = f.BooleanField(label="Assign Markers", required=False)
    visible_to_developer = f.BooleanField(label="Visible to developer", required=False)
