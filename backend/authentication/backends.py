# authentication/backends.py

import logging
from ldap3 import Server, Connection, ALL, SUBTREE
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ObjectDoesNotExist
from authentication.models import CustomUser
import environ
from pathlib import Path

env = environ.Env()
#environ.Env.read_env()
env.read_env(Path(__file__).resolve().parent.parent / 'core' / '.env')

logger = logging.getLogger('django_auth_ldap')

class CustomLDAPBackend(BaseBackend):
    def __init__(self):
        self.server_uri = env('LDAP_SERVER_URI')
        self.bind_dn = env('LDAP_BIND_DN')
        self.bind_password = env('LDAP_BIND_PASSWORD')
        self.search_base = env('LDAP_SEARCH_BASE')
        self.search_filter = "(sAMAccountName=%(user)s)"
        self.server = Server(self.server_uri, get_info=ALL)
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        username = username or kwargs.get('username')
        password = password or kwargs.get('password')

        logger.debug(f'CustomLDAPBackend authenticate called with username={username}')

        if not username or not password:
            logger.debug('Missing username or password, falling back')
            return None

        # LDAP admin bind and search
        admin_conn = Connection(self.server, user=self.bind_dn, password=self.bind_password, auto_bind=True)
        if not admin_conn.bind():
            logger.error(f'Admin bind failed: {admin_conn.result}')
            return None

        user_search_filter = self.search_filter % {'user': username}
        logger.debug(f'Searching with filter: {user_search_filter}')
        admin_conn.search(self.search_base, user_search_filter, attributes=['distinguishedName'])

        if len(admin_conn.entries) == 0:
            logger.debug(f'No user found for filter: {user_search_filter}')
            return None  # <--- important for fallback

        user_dn = admin_conn.entries[0].distinguishedName.value
        logger.debug(f'User DN: {user_dn}')

        user_conn = Connection(self.server, user=user_dn, password=password)
        if user_conn.bind():
            logger.debug('User bind successful')
            try:
                user = CustomUser.objects.get(username=username)
            except ObjectDoesNotExist:
                user = CustomUser(username=username)
                user.save()
            return user
        else:
            logger.error(f'User bind failed: {user_conn.result}')
            return None

    
    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
