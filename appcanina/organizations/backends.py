from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Allow a unique email address without overriding existing usernames."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not isinstance(username, str) or password is None or "@" not in username:
            return None
        identifier = username.strip()
        User = get_user_model()
        # An exact username always belongs to its original account.
        if User.objects.filter(username=identifier).exists():
            return None
        users = list(User.objects.filter(email__iexact=identifier)[:2])
        if len(users) != 1:
            User().set_password(password)
            return None
        user = users[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
