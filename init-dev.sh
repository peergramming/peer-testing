#!/usr/bin/env bash
rm db.sqlite3
rm -r common/migrations feedback/migrations var
mkdir var
mkdir var/test
mkdir var/uploads
./manage.py makemigrations common feedback
./manage.py migrate
./manage.py collectstatic --noinput
setfacl -Rm u:apache:r-x common feedback patool runner teacher file_viewer libs notify student templates test_match var/static
setfacl -m u:apache:rwx var
setfacl -Rm u:apache:rwx var/test var/uploads
setfacl -Rdm u:lm356:rwx var/test var/uploads
touch db.sqlite3
setfacl -m u:apache:rw- db.sqlite3
./manage.py shell -c "
from test.prepare_database import prepare_database
prepare_database()
"
