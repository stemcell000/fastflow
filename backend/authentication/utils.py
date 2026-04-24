import os

from authentication.models import CustomUser as User
from core import settings

class Utils:
    def username_exists(username):
        user_query = User.objects.filter(username=username)
        if user_query.exists():
            return user_query.first()

        return False


    def email_exists(email):
        user_query = User.objects.filter(email=email)

        if user_query.exists():
            return user_query.first()

        return False


    def delete_user(to_delete_user_username):
        user = User.objects.filter(username=to_delete_user_username)
        if user.count() == 0:
            return False, 'User not found.'
        if user.last().is_superuser:
            return False, 'Cannot delete superuser.'
        try:
            user.delete()
        except Exception as e:
            return False, str(e)
        return True, f'{to_delete_user_username} deleted successfully.'


