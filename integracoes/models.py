from django.db import models

class StravaAccount(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name="strava_account", blank=True, null=True)

    # Dados do atleta
    strava_id = models.BigIntegerField(unique=True)
    firstname = models.CharField(max_length=100, blank=True, null=True)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    profile_url = models.URLField(blank=True, null=True)

    # Tokens da API
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_expires_at = models.IntegerField()  # timestamp UNIX

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.user.email})"
    
class GoogleContactsIntegration(models.Model):
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE)
    google_account_id = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    token_expiry = models.DateTimeField()
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scope = models.TextField(null=True, blank=True)

    @classmethod
    def get_for_user(cls, user):
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return None

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.token_expiry

    def __str__(self):
        return f"Google Contacts - {self.user}"


