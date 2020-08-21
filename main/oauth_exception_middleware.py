from social_django.middleware import SocialAuthExceptionMiddleware
from social_core import exceptions as social_exceptions
from django.http import HttpResponse
from django.conf import settings
import logging

logger = logging.getLogger("django")

class PeerTestingSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if hasattr(social_exceptions, exception.__class__.__name__):
            logging.error("Authentication error: %s" % exception)
            return HttpResponse("Exception %s while processing your social account. An error occured during the authentication process." % exception)
        else:
            return super(PeerTestingSocialAuthExceptionMiddleware, self).process_exception(request, exception)
