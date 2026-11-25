from django.contrib.auth.backends import ModelBackend

from .models import User


class ApprovedAccountBackend(ModelBackend):
    def user_can_authenticate(self, user):
        # ModelBackend also calls this when loading an existing session.
        return (super().user_can_authenticate(user) and
                user.account_status == User.AccountStatus.APPROVED and
                user.role in User.Role.values)
