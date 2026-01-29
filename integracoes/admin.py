from django.contrib import admin
from .models import StravaAccount, GoogleContactsIntegration

admin.site.register(StravaAccount)
admin.site.register(GoogleContactsIntegration)

