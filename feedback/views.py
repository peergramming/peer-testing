from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

import json

import common.models as cm
from . import forms as f
from . import models as m
from common.permissions import require_teacher
import common.permissions as p

PEER_NICK_PREFIX = "Peer #"

@login_required()
@require_teacher
def modify(request):
    if request.method != "POST":
        return HttpResponseForbidden("You're only allowed to post stuff here")
    form = f.FeedbackGroupForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("This form is not valid")
    coursework = cm.Coursework.objects.get(id=form.cleaned_data['coursework'])
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You're not enrolled on the course")
    if form.cleaned_data['groupid'] == '':
        group = save_new_feedback_group(form.cleaned_data["students"], coursework)
        return HttpResponse("Group Added: " + str(group.id))
    else:
        group = m.FeedbackGroup.objects.get(id=form.cleaned_data['groupid'])
        modify_existing_feedback_group(group, form.cleaned_data["students"])
        return HttpResponse("Group Modified: " + str(group.id))


@transaction.atomic()
def save_new_feedback_group(students, coursework):
    """save and return a new instance of a feedback group model
    and populate with the @students and @coursework. Note:
    This method does no validation of if a user is enrolled on
    a course, as we may wish to be able to re-use these
    groups across courses"""
    group = m.FeedbackGroup(coursework=coursework)
    group.save()
    count = 1
    new_students = students.strip().strip(',').split(',')
    new_students_list = list(map(lambda w: w.strip(), new_students))
    for student in new_students_list:
        m.FeedbackMembership(group=group,
                             user=User.objects.get(username=student),
                             nickname="%s%s" % (PEER_NICK_PREFIX, str(count))).save()
        count += 1
    return group

@transaction.atomic()
def modify_existing_feedback_group(feedback_group, new_students):
    """Given an already existing @feedback_group, and some
    @new_students, go through this and update accordingly"""

    new_students = new_students.strip().strip(',').split(',')
    new_students_list = list(map(lambda w: w.strip(), new_students))

    members = m.FeedbackMembership.objects.filter(group=feedback_group)
    count = get_member_count_for_naming(members)
    for member in members:
        if str(member.login) not in new_students_list:
            member.delete()
    for member in new_students_list:
        current_user = m.User.objects.get(username=member)
        exists = m.FeedbackMembership.objects.filter(user=current_user, group=feedback_group)
        if exists.count() != 1:
            m.FeedbackMembership(user=current_user,
                                 group=feedback_group,
                                 nickname="%s%s" % (PEER_NICK_PREFIX, str(count))).save()
            count += 1


def get_member_count_for_naming(existing_members):
    """Determine the highest number assigned to a peer's nickname
    in @existing_members in order to name more without collision.
    assumes that prefix is 'Peer #' in nicknames"""
    ids = [m.nickname[len(PEER_NICK_PREFIX):] for m in existing_members]
    ids.sort()
    return int(ids[-1]) + 1


@login_required()
@require_teacher
@transaction.atomic()
def delete(request):
    if request.method != "POST":
        return HttpResponseForbidden("You're only allowed to post stuff here")
    form = f.FeedbackGroupForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("This form is not valid")
    coursework = cm.Coursework.objects.get(id=form.cleaned_data['coursework'])
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You're not enrolled on the course")
    if form.cleaned_data['groupid'] is None:
        return HttpResponse("Group Doesn't Exist - No Action Taken")
    m.FeedbackGroup.objects.get(id=form.cleaned_data['groupid']).delete()
    return HttpResponse("Group Deleted")


@login_required()
@require_teacher
@transaction.atomic()
def export_data(request):
    if request.method != "POST":
        return HttpResponseForbidden("You're only allowed to post stuff here")
    coursework = cm.Coursework.objects.get(id=request.POST["coursework_id"])
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You're not enrolled on the course")
    data = [','.join([member.user.username for member in
                m.FeedbackMembership.objects.filter(group=feedback_group)])
                for feedback_group in m.FeedbackGroup.objects.filter(coursework=coursework)]
    return HttpResponse(json.dumps(data))


@login_required()
@require_teacher
@transaction.atomic()
def import_data(request):
    if request.method != "POST":
        return HttpResponseForbidden("You're only allowed to post stuff here")
    coursework = cm.Coursework.objects.get(id=request.POST["coursework_id"])
    if not p.is_enrolled_on_course(request.user, coursework.course):
        return HttpResponseForbidden("You're not enrolled on the course")
    data = json.loads(request.POST["json_data"])
    for students in data:
        save_new_feedback_group(students, coursework)
    return HttpResponse("Groups Created")
