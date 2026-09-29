from rest_framework import serializers
from authentication.models import CustomUserCategory

class CustomUserCategorySerializer(serializers.ModelSerializer):
    """Serializer for user categories"""
    
    class Meta:
        model = CustomUserCategory
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']