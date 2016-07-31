from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class AuthenticationBackend(ModelBackend):
    def get_user(self, user_id):
        try:
            return User.objects.select_related('preferences').get(pk=user_id)
        except User.DoesNotExist:
            return None
