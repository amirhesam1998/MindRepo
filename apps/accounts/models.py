from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """MindRepo's extensible user model; profile fields are intentionally deferred."""
