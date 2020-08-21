import django.forms as f
from . import models as m


class FeedbackGroupForm(f.Form):
    """Form used to change students in a group, comma separated usernames"""
    students = f.CharField(widget=f.Textarea, label="Comma-Separated Users in this group")
    groupid = f.CharField(max_length=64, required=False)
    coursework = f.SlugField(max_length=8, widget=f.HiddenInput)


def get_feedback_groups_as_iterable_forms(coursework):
    """For the given @coursework instance, get all of the
    feedback groups that are associated with this coursework
    and return their contents as an iterable list of initial dicts
    so that forms may be generated"""
    return [get_feedback_as_form(coursework, fg) for fg in
            m.FeedbackGroup.objects.filter(coursework=coursework)]


def get_feedback_as_form(coursework, feedback_group):
    """Given a @feedback_group instance, generate a dict that
    could be used to generate a form with initial values,
    using the specified @coursework as the coursework"""
    return {"coursework": coursework.id,
            "students": ','.join([member.user.username for member in
                                  m.FeedbackMembership.objects.filter(group=feedback_group)]),
            "groupid": feedback_group.id}
