from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (SettingViewSet, UserCategoryViewSet)

router = DefaultRouter()
router.register(r'settings', SettingViewSet, basename='setting')
router.register(r'categories', UserCategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]
