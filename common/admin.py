from django.contrib import admin
import common.models as m

admin.site.register(m.Course)
admin.site.register(m.EnrolledUser)
admin.site.register(m.Coursework)
admin.site.register(m.Submission)
admin.site.register(m.TestMatch)
