from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.models import User, Group

import requests

import logging
logger = logging.getLogger("django")

from main import local
gitlab_project_api = local.SOCIAL_AUTH_GITLAB_API_URL + '/api/v4/projects/'

def add_notification(user,cw,message):
    """Adds a GitLab comment @message to @user's latest commit of @cw"""
    logger.info("Add peer-testing notification for " + user)
    gitlab_cw = user + "%2F" + str(cw)
    gitlab_commits_comments = "/repository/commits/master/comments"
    gitlab_data = { 'note' : '@' + user + ' ' + message}
    gitlab_req = gitlab_project_api + gitlab_cw + gitlab_commits_comments
    logger.info("Add peer-testing notification, API request: " + gitlab_req)
    response = requests.post( gitlab_req,
                              data=gitlab_data,
                              params={'access_token': settings.PEER_TESTING_API_ACCESS_TOKEN},
                             verify=False )
    gitlab_info = str(response.__dict__)
    content=response.content
    logger.info("Add peer-testing notification, gitlab response: " + str(content))

def add_peer_testing_as_reporter(request,cw):
   social = request.user.social_auth.get(provider='gitlab')
   gitlab_cw = str(request.user) + "%2F" + str(cw.name)
   gitlab_params = {'access_token': social.extra_data['access_token']}
   # Adding Peer-Testing to project as Reporter
   logger.info("Add Peer-Testing as Raporter to " + gitlab_cw)
   gitlab_add_pt_rep_data = { 'user_id' : local.GITLAB_PT_USER_ID,
                              'access_level' : local.GITLAB_PT_USER_ACCESS_LEVEL }
   gitlab_add_pt_rep_req = gitlab_api_projects + gitlab_cw + "/members"
   resp_add_pt_rep = requests.post(gitlab_add_pt_rep_req,
                                   data=gitlab_add_pt_rep_data,
                                   params=gitlab_params,
                                   verify=False)
   logger.info("Add Peer-Testing as Raporter to %s: %s" % (gitlab_cw, resp_add_pt_rep.content))
