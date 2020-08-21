import os
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import transaction
from common import models as m
import csv
import logging

logger = logging.getLogger("django")

def enrol_new_user(backend, details, user=None, *args, **kwargs):
    # Getting user's email address
    # email = user.email
    logger.info('New user')
    logger.info('    user.email ' + user.email)
    logger.info('    details.get(email) ' + details.get('email'))
    email = details.get('email').lower()

    # Changing username into usual userid
    userid=email[:-9].lower()
    if user:
        if not User.objects.filter(username=userid).exists():
            user.username = userid
            user.save()

    # Enrol user according to csv file records
    if email:
        logger.info('New user (' + email + ')')
        with open(os.path.join(settings.BASE_DIR,'roles.csv')) as rolescsvfile:
            roles = csv.DictReader(rolescsvfile)
            for reg in roles:
                if reg['email'] == email:
                    role=reg['role']
                    coursecode=reg['course']
                    group=Group.objects.get(name=role)
                    group.user_set.add(user)
                    course = m.Course.objects.get(code=coursecode)
                    user.groups.add(group)
                    user.save()
                    if not m.EnrolledUser.objects.filter(login=user, course=course).exists():
                        m.EnrolledUser(login=user, course=course).save()
                        logger.info('Enrolment of ' + userid + ' to ' + coursecode + ' as ' + role)
    else:
        logger.info('New user (no email)')
