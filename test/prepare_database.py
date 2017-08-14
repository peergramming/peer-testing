
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import transaction
from common import models as m


@transaction.atomic
def prepare_database():
    """Populate the database with some testing data.
    Creates some teacher, some students, and some coursework tasks"""
    if not settings.DEBUG:
        print("Can only prepare test database when in debug mode")
        return

    User.objects.create_superuser(username='admin@pt.macs.hw.ac.uk',
                                  email='admin@pt.macs.hw.ac.uk',
                                  password='Lancelot')

    t = Group()
    t.name = "teacher"
    t.save()
    s = Group()
    s.name = "student"
    s.save()
    fem = Group()
    fem.name = "female"
    fem.save()
    mal = Group()
    mal.name = "male"
    mal.save()
    edi = Group()
    edi.name = "edinburgh"
    edi.save()
    dub = Group()
    dub.name = "dubai"
    dub.save()

    cu = User.objects.create_user

    l = cu("lm356@pt.macs.hw.ac.uk", email="lm356@pt.macs.hw.ac.uk", password="Sutherland")
    l.groups.add(t)
    l.save()

    a = cu("alex@pt.macs.hw.ac.uk", email="alex@pt.macs.hw.ac.uk", password="Glasgow")
    a.groups.add(s)
    a.save()

    c = cu("connie@pt.macs.hw.ac.uk", email="connie@pt.macs.hw.ac.uk", password="Ganymede")
    c.groups.add(s)
    c.save()

    course = m.Course(name="Example Course", code="EX2017A")
    course.save()
    m.EnrolledUser(login=l, course=course).save()
    m.EnrolledUser(login=a, course=course).save()
    m.EnrolledUser(login=c, course=course).save()
