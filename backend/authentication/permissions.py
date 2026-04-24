from rest_framework.permissions import BasePermission


class IsNetworkManager(BasePermission):
    """
    Permission pour les Network & Identity Managers
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_network_manager
        )