#!/usr/bin/env bash
echo Resetting the stored data for peer-testing. This will delete everything. Press enter to continue.
read -n 1

# Reset the stored data for peer-testing. This will delete everything.
rm db.sqlite3
rm -r common/migrations feedback/migrations var

# Re-make the required data storage directories
mkdir var
mkdir var/test
mkdir var/uploads
mkdir var/log
mkdir notify

# Set up django
./manage.py makemigrations common feedback
./manage.py migrate
./manage.py collectstatic --noinput
touch db.sqlite3

# Make the test runner scripts usable
# If you add your own make sure to make them executable
chmod +x libs/junit.sh
chmod +x libs/python.sh

# Set the apache to to be able to access the peer testing directory and application
# Assume apache is running unde the user "apache"
# This can be commented out if just developing / debugging locally
setfacl -m u:apache:rx .
setfacl -m u:apache:rx main

# Set up appropriate permissions for those who want to access peer testing
# In this example, django is running under the user "peer", and a teacher admin is running under "teacher"
# This can be commented out if just developing / debugging locally
setfacl -Rm u:peer:r-x common feedback main runner teacher file_viewer libs notify student templates test_match var/static
chmod g+w .
setfacl -m u:peer:rwx .
setfacl -m u:peer:rwx var
setfacl -Rm u:peer:rwx var/test var/uploads var/log
setfacl -Rdm u:teacher:rwx var/test var/uploads var/log
setfacl -m u:peer:rw- db.sqlite3

# Populate an initial database with a superuser, required groups and an initial course
./manage.py shell -c "
from django.contrib.auth.models import User, Group
from common import models as m
User.objects.create_superuser(username='admin',
                                email='admin@peer-testing',
                                password='a secure password')

course = m.Course(name='My Programming Course (2019-20)', code='1920-MPC')
course.save()

t = Group()
t.name = 'teacher'
t.save()

s = Group()
s.name = 'student'
s.save()
"
