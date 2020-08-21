"""
THIS CONTENTS OF THIS FILE SHOULD BE COPIED TO A NEW
FILE CALLED local.py. THIS NEW FILE SHOULD NOT BE
ADDED TO VERSION CONTROL. THIS DEFAULT FILE SHOULD
BE KEPT AS-IS WITHIN VERSION CONTROL.
"""

LOCAL_BASE_DIR = "PATH/website"
# Define the base location the application is stored in
# This should be a fully qualified path to the directory
# which contains manage.py

SECRET = ""
# A sufficiently random string to use for deriving security

# Location of gitlab
SOCIAL_AUTH_GITLAB_API_URL = ''
# Peer-testing "bot" user within gitlab - should be a number
GITLAB_PT_USER_ID = 000
GITLAB_PT_USER_ACCESS_LEVEL = 20

HTTP_PREFIX = '/peer-testing'
# if this is beign served as a sub-site of another, specify
# the prefix with leading slash and NO trailing slash
# e.g. if this is beign served at 
# http://example.com/peer-testing/student/etc
# this prefix should read as
# HTTP_PREFIX = "/peer-testing"
# If there is no prefix required, leave this blank


WHITELISTED_EMAILS = ['user1@example.com', 'user2@example.com']
WHITELISTED_DOMAINS = ['example.com']
# List of emails and domains authorized to register
# Also listable in roles.csv

HOSTS = ["your.domain.co.uk"]
# Add localhosts here for debug

# If you want to collect research data from students
# Will display if there is a non-empty string of research blurb html
RESEARCH_QUESIONNAIRE_URL = 'https://forms.office.com/Pages/ResponsePage.aspx?id=blah&embed=true'
RESEARCH_BLURB_RAW_HTML = '''
You should include a brief description of the research project
as well as a contact email if students hve enquiries
<a href="mailto:me@example.com">Researcher Name</a>'''

# List of admin users. Pair of name & email
LOCAL_ADMINS = [('Admin Name', 'admin@example.com')]

