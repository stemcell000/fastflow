from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    LogoutView,
    LDAPTokenObtainPairView,
    CookieTokenRefreshView,
    MeView,
    SyncLDAPUsersView,
    CustomUserViewSet,
    LDAPGroupViewSet,
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'ldap-groups', LDAPGroupViewSet, basename='ldap-group')

urlpatterns = [
    # Authentication endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/', LDAPTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),  # ← IMPORTANT
    path('sync-ldap/', SyncLDAPUsersView.as_view(), name='sync_ldap'),
    
    # Include router URLs (users/, categories/, ldap-groups/)
    path('', include(router.urls)),
]