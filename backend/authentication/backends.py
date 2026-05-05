import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class RestrictedModelBackend(ModelBackend):
    """
    Fallback sur la table Django — uniquement pour is_staff et is_superuser.

    Déclenché automatiquement par Django quand LDAPBackend retourne None, ce qui
    arrive dans les cas suivants :
      - Serveur LDAP injoignable (poste hors réseau, panne)
      - Mauvais LDAP_BIND_DN / LDAP_BIND_PASSWORD
      - Utilisateur non trouvé dans l'AD

    Note : django-auth-ldap avale silencieusement les LDAPError et retourne None,
    ce qui permet à Django de passer au backend suivant sans lever d'exception.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        # Restriction : uniquement staff et superuser
        if not (user.is_staff or user.is_superuser):
            logger.debug(
                "Fallback table refusé pour '%s' — non staff/superuser", username
            )
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.info(
                "Utilisateur '%s' authentifié via fallback table (LDAP indisponible)",
                username,
            )
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
