from rest_framework import serializers
from authentication.models import LDAPGroup


# Import circulaire résolu en lazy import
def get_user_minimal_serializer():
    from .user_serializer import CustomUserMinimalSerializer
    return CustomUserMinimalSerializer


class LDAPGroupSerializer(serializers.ModelSerializer):
    """Serializer pour les groupes LDAP"""
    
    members_count = serializers.SerializerMethodField()
    managers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LDAPGroup
        fields = [
            'id',
            'name',
            'distinguished_name',
            'description',
            'managers',
            'members_count',
            'managers_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.members.count()
    
    def get_managers_count(self, obj):
        return obj.managers.count()

class LDAPGroupListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour les listes de groupes LDAP"""
    
    members_count = serializers.SerializerMethodField()
    managers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LDAPGroup
        fields = [
            'id',
            'name',
            'distinguished_name',
            'members_count',
            'managers_count',
        ]
    
    def get_members_count(self, obj):
        return obj.members.count()
    
    def get_managers_count(self, obj):
        return obj.managers.count()


class LDAPGroupDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un groupe LDAP avec ses membres et managers"""
    
    members_count = serializers.SerializerMethodField()
    managers_count = serializers.SerializerMethodField()
    
    # Utilisation de SerializerMethodField pour éviter l'import circulaire
    members = serializers.SerializerMethodField()
    managers_info = serializers.SerializerMethodField()
    
    class Meta:
        model = LDAPGroup
        fields = [
            'id',
            'name',
            'distinguished_name',
            'description',
            'managers',
            'managers_info',
            'managers_count',
            'members',
            'members_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.members.count()
    
    def get_managers_count(self, obj):
        return obj.managers.count()
    
    def get_members(self, obj):
        UserMinimalSerializer = get_user_minimal_serializer()
        return UserMinimalSerializer(obj.members.all(), many=True).data
    
    def get_managers_info(self, obj):
        UserMinimalSerializer = get_user_minimal_serializer()
        return UserMinimalSerializer(obj.managers.all(), many=True).data