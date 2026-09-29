"""
backend URL Configuration
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.views import HomeView

urlpatterns = [
    # Frontend application home (requires an authenticated session)
    path('', login_required(HomeView.as_view()), name='home'),

    # HTML login/logout for the frontend (Django session, goes through
    # AUTHENTICATION_BACKENDS: LDAP then staff/superuser fallback).
    # Distinct from /auth/login/ (JSON/JWT API of the authentication app).
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='portal_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='portal_logout'),

    # Django admin
    path('admin/', admin.site.urls),

    # DRF Browsable API (web interface)
    path('api-auth/', include('rest_framework.urls')),

    # Applications
    path('auth/', include('authentication.urls')),  # ← /auth/ (nginx strips /api/)
    path('settings/', include('api.urls')),         # ← /settings/ for UserCategory, etc.
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)