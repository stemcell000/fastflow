"""
backend URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # API REST Framework Browsable API (interface web DRF)
    path('api-auth/', include('rest_framework.urls')),
    
    # Applications
    path('auth/', include('authentication.urls')),  # ← /auth/ (nginx enlève /api/)
    path('settings/', include('api.urls')),         # ← /settings/ pour UserCategory, etc.
]

# Servir les fichiers media et static en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)