# Remove the CustomUser model if it exists

from django.db import models
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token as AuthToken

class Token(AuthToken):
    expires = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.expires:
            self.expires = timezone.now() + timedelta(days=1)
        super().save(*args, **kwargs)
