from django.db import models

# Create your models here.
from django.db import models

class StravaAccount(models.Model):
    strava_id = models.CharField(max_length=50, unique=True)
    firstname = models.CharField(max_length=100, blank=True, null=True)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    profile_url = models.URLField(blank=True, null=True)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expires_at = models.DateTimeField()

    def __str__(self):
        return self.athlete_name or f"Strava User {self.strava_id}"
