"""Forms accessible to the entire django project"""

import django.forms as f


class EasyMatchForm(f.Form):
    """A form to show available tests, solutions for creating a test match
    within a specific group"""
    test = f.ChoiceField(label="A test case to run")
    solution = f.ChoiceField(label="A solution to test")
    feedback_group = f.CharField(max_length=64, widget=f.HiddenInput, required=False)

    def __init__(self, tests, solutions, *args, **kwargs):
        """Initialise the form with a list of tuples of @tests and
        @solutions. the tuples denote the submission ID and display
        name. You should also add the feedback group here as
        initial={"feedback_group": XXXXX}"""
        super(EasyMatchForm, self).__init__(*args, **kwargs)
        self.fields['test'].choices = tests
        self.fields['solution'].choices = solutions
