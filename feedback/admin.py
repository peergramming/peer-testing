from django.contrib import admin
import feedback.models as m

admin.site.register(m.FeedbackGroup)
admin.site.register(m.FeedbackMembership)
admin.site.register(m.TestAccessControl)
