from django.conf import settings

# Logout link to use in templates. If followed, the link would:
# - log the user out of Office365
# - redirect the user to the logout facility of this site
# - the session on the site would then be terminated
def logout_url(request):
    logout_url = ''
#    logout_url = 'https://login.microsoftonline.com/' \
#                 + settings.SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_TENANT_ID \
#                 + '/oauth2/logout?post_logout_redirect_uri=' \
#                 + request.build_absolute_uri('/') \
#                 + settings.MEDIA_URL \
#                 + '/logout/'
    return {'logout_url': logout_url}

