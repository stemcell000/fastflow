# api/views.py

from rest_framework import viewsets, permissions
from .models import Setting
from authentication.models.custom_user_category import CustomUserCategory
from .serializers import (SettingSerializer, CustomUserCategorySerializer)
from rest_framework.response import Response

class SettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les paramètres de l'application
    """
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        settings = self.get_queryset()
        serializer = self.get_serializer(settings, many=True)
        return Response(serializer.data)
    

class UserCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les catégories d'utilisateurs
    """
    queryset = CustomUserCategory.objects.all()
    serializer_class = CustomUserCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None