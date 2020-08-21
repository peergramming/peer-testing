import os
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction

import json

from . import models as fm

import csv

import logging

PEER_NICK_PREFIX = "Peer #"

logger = logging.getLogger("django")

def get_member_count_for_naming(existing_members):
    """Determine the highest number assigned to a peer's nickname
    in @existing_members in order to name more without collision.
    assumes that prefix is 'Peer #' in nicknames"""
    ids = [fm.nickname[len(PEER_NICK_PREFIX):] for fm in existing_members]
    ids.sort()
    if len(ids) == 0:
        return 1
    else:
        return int(ids[-1]) + 1

def add_student_in_existing_feedback_group(feedback_group_id, new_student):
    """Given an already existing @feedback_group_string, add a @new_student to the group"""

    feedback_group=fm.FeedbackGroup.objects.get(id=feedback_group_id)
    logger.info('Add to group ' + feedback_group_id + ', to add ' + new_student)
    new_student = new_student.strip()

    members = fm.FeedbackMembership.objects.filter(group=feedback_group)
    count = get_member_count_for_naming(members)
    logger.info('Add to group ' + feedback_group_id + ' current count ' + str(count))
    current_user = fm.User.objects.get(username=new_student)
    exists = fm.FeedbackMembership.objects.filter(user=current_user, group=feedback_group)
    logger.info('Add to group ' + feedback_group_id + ' exists ' + str(exists))
    if exists.count() != 1:
        fm.FeedbackMembership(user=current_user,
                             group=feedback_group,
                             nickname="%s%s" % (PEER_NICK_PREFIX, str(count))).save()

def add_all_students_to_feedback_groups():
    logger.info('Start adding all students to feedback groups')
    with open(os.path.join(settings.BASE_DIR,'groups.csv')) as groupscsvfile:
        rows = csv.DictReader(groupscsvfile)
        for row in rows:
            group_id=row['group_id'].strip()
            user_ids=row['user_ids'].strip()
            group_exists=fm.FeedbackGroup.objects.filter(id=group_id).exists()
            if not group_exists:
                # TODO creating appropriate group
                logger.info('Missing group ' + group_id)
            else:
                feedback_group=fm.FeedbackGroup.objects.get(id=group_id)
                members = fm.FeedbackMembership.objects.filter(group=feedback_group)
                count = get_member_count_for_naming(members)
                for user_id in user_ids.strip().split(','):
                    user_exists = fm.User.objects.filter(username=user_id).exists()
                    if not user_exists:
                        logger.info('Missing user ' + user_id)
                    else:
                        current_user = fm.User.objects.get(username=user_id)
                        exists = fm.FeedbackMembership.objects.filter(user=current_user, group=group_id).exists()
                        if not exists:
                            fm.FeedbackMembership(user=current_user,
                                                 group=feedback_group,
                                                 nickname="%s%s" % (PEER_NICK_PREFIX, str(count))).save()
                            count=count+1
                            logger.info('Add ' + user_id + ' to group ' + group_id)
    logger.info('End adding all students to feedback groups')
