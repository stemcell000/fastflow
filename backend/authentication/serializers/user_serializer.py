from rest_framework import serializers
from django.contrib.auth import get_user_model
from authentication.models import CustomUserCategory

User = get_user_model()


class CustomUserMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les références"""
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name_display',
            'email',
        ]


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer principal pour CustomUser"""
    
    is_admin = serializers.SerializerMethodField()
    is_user = serializers.SerializerMethodField()
    is_director = serializers.BooleanField(read_only=True)
    is_network_manager = serializers.SerializerMethodField()  # ← AJOUTER
    is_network_admin = serializers.SerializerMethodField() 
    
    category = serializers.PrimaryKeyRelatedField(
        queryset=CustomUserCategory.objects.all(),
        required=False,
        allow_null=True,
        read_only=False
    )
    
    # ✅ Utiliser SerializerMethodField au lieu d'imports directs
    category_detail = serializers.SerializerMethodField()
    ldap_groups_info = serializers.SerializerMethodField()  # ← CORRECTION ICI
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    ldap_group_names = serializers.ListField(source='get_ldap_group_names', read_only=True)
    
    # Propriétés de mot de passe
    password_expiration_date = serializers.DateTimeField(read_only=True)
    days_until_password_expires = serializers.IntegerField(read_only=True)
    is_password_expired = serializers.BooleanField(read_only=True)
    password_expires_soon = serializers.BooleanField(read_only=True)
    
    # Propriétés de compte LDAP
    is_ldap_account_expired = serializers.BooleanField(read_only=True)
    days_since_last_ldap_logon = serializers.IntegerField(read_only=True)
    days_since_password_change = serializers.IntegerField(read_only=True)
    group_count = serializers.IntegerField(source='get_group_count', read_only=True)
    
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'username',
            'email',
            'is_active',
            'is_admin',
            'is_superuser',
            'is_user',
            'is_director',
            'is_network_manager',
            'is_network_admin',
            'full_name_display',
            'category',
            'category_detail',
            'avatar',
            'avatar_url',
            'is_staff',
            'ldap_created_date',
            'ldap_modified_date',
            'ldap_last_logon',
            'ldap_password_last_set',
            'ldap_account_expires',
            'ldap_last_sync',
            'ldap_groups',
            'ldap_groups_info',
            'ldap_group_names',
            'group_count',
            'password_expiration_date',
            'days_until_password_expires',
            'is_password_expired',
            'password_expires_soon',
            'is_ldap_account_expired',
            'days_since_last_ldap_logon',
            'days_since_password_change',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'date_joined',
            'last_login',
            'ldap_created_date',
            'ldap_modified_date',
            'ldap_last_logon',
            'ldap_password_last_set',
            'ldap_account_expires',
            'ldap_last_sync',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def get_is_admin(self, obj):
        return (obj.is_active and (obj.is_staff or obj.is_superuser))
    
    def get_is_user(self, obj):
        return obj.is_active and not (obj.is_staff or obj.is_superuser)
        
    def get_is_network_manager(self, obj):
        """Retourne True si l'utilisateur est Network admin"""
        return obj.is_network_manager
    
    def get_is_network_admin(self, obj):
        """Alias pour is_network_manager"""
        return obj.is_network_manager
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_category_detail(self, obj):
        """Import lazy pour éviter l'import circulaire"""
        if not obj.category:
            return None
        from .user_category_serializer import CustomUserCategorySerializer
        return CustomUserCategorySerializer(obj.category).data
    
    def get_ldap_groups_info(self, obj):
        """Import lazy pour éviter l'import circulaire"""
        from .ldap_group_serializer import LDAPGroupSerializer
        return LDAPGroupSerializer(obj.ldap_groups.all(), many=True).data


class UserCollectionSerializer(serializers.ModelSerializer):
    """Serializer allégé pour les collections/listes"""
    
    is_admin = serializers.SerializerMethodField()
    full_name_display = serializers.CharField(source='full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'full_name_display',
            'is_active',
            'is_admin',
            'is_superuser',
            'category'
        ]

    def get_is_admin(self, obj):
        return (obj.is_active and (obj.is_staff or obj.is_superuser))


class CustomUserListSerializer(serializers.ModelSerializer):
    """Serializer allégé pour les listes d'utilisateurs"""
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    avatar_url = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_network_manager = serializers.SerializerMethodField()
    password_expires_soon = serializers.BooleanField(read_only=True)
    is_ldap_account_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name_display',
            'is_active',
            'is_staff',
            'is_admin',
            'is_network_manager', 
            'avatar_url',
            'category_name',
            'password_expires_soon',
            'is_ldap_account_expired',
        ]
    
    def get_is_admin(self, obj):
        return (obj.is_active and (obj.is_staff or obj.is_superuser))
    
    def get_is_network_manager(self, obj):
        return obj.is_network_manager
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création d'utilisateurs"""
    
    password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_director',
            'category',
            'avatar',
        ]
    
    def validate(self, data):
        password = data.get('password')
        password_confirm = data.pop('password_confirm', None)
        
        if password and password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas'
            })
        
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
        
        return user


class CustomUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour d'utilisateurs"""
    
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_director',
            'category',
            'avatar',
        ]


class CustomUserPasswordChangeSerializer(serializers.Serializer):
    """Serializer pour le changement de mot de passe"""
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Les nouveaux mots de passe ne correspondent pas'
            })
        
        if len(data['new_password']) < 8:
            raise serializers.ValidationError({
                'new_password': 'Le mot de passe doit contenir au moins 8 caractères'
            })
        
        return data
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('L\'ancien mot de passe est incorrect')
        return value


class CustomUserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour le profil utilisateur"""
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    category_detail = serializers.SerializerMethodField()
    ldap_group_names = serializers.ListField(source='get_ldap_group_names', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    password_expires_soon = serializers.BooleanField(read_only=True)
    days_until_password_expires = serializers.IntegerField(read_only=True)
    is_password_expired = serializers.BooleanField(read_only=True)
    current_hr_folder = serializers.SerializerMethodField()
    pending_access_requests_count = serializers.SerializerMethodField()
    pending_supervised_requests_count = serializers.SerializerMethodField()
    is_network_manager = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name_display',
            'is_active',
            'is_staff',
            'is_admin',
            'is_director',
            'is_network_manager',
            'is_human',
            'avatar',
            'avatar_url',
            'category_detail',
            'ldap_group_names',
            'password_expires_soon',
            'days_until_password_expires',
            'is_password_expired',
            'ldap_last_logon',
            'date_joined',
            'last_login',
            'current_hr_folder',
            'pending_access_requests_count',
            'pending_supervised_requests_count',
        ]
        read_only_fields = [
            'date_joined',
            'last_login',
            'ldap_last_logon',
        ]
    
    def get_is_admin(self, obj):
        return (obj.is_active and (obj.is_staff or obj.is_superuser))
    
    def get_is_network_manager(self, obj):
        return obj.is_network_manager
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_category_detail(self, obj):
        if not obj.category:
            return None
        from .user_category_serializer import CustomUserCategorySerializer
        return CustomUserCategorySerializer(obj.category).data
    
    def get_current_hr_folder(self, obj):
        try:
            from hr.models import UserFolder
            folder = obj.hr_folders.filter(is_current=True).first()
            if folder:
                return {
                    'id': folder.id,
                    'position': folder.position,
                    'department': folder.department,
                    'hire_date': folder.hire_date,
                    'contract_type': folder.contract_type,
                    'status': folder.status,
                }
        except:
            pass
        return None
    
    def get_pending_access_requests_count(self, obj):
        try:
            from hr.models import AccessRequest
            return obj.access_requests.filter(validation_status='PENDING').count()
        except:
            return 0
    
    def get_pending_supervised_requests_count(self, obj):
        try:
            from hr.models import AccessRequest
            managed_groups = obj.managed_ldap_groups.all()
            return AccessRequest.objects.filter(
                ldap_group__in=managed_groups,
                validation_status='PENDING'
            ).count()
        except:
            return 0


class LDAPSyncStatusSerializer(serializers.ModelSerializer):
    """Serializer pour le statut de synchronisation LDAP"""
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    ldap_group_names = serializers.ListField(source='get_ldap_group_names', read_only=True)
    days_since_last_sync = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name_display',
            'ldap_created_date',
            'ldap_modified_date',
            'ldap_last_logon',
            'ldap_password_last_set',
            'ldap_account_expires',
            'ldap_last_sync',
            'days_since_last_sync',
            'ldap_group_names',
            'is_ldap_account_expired',
            'is_password_expired',
            'password_expires_soon',
            'days_until_password_expires',
        ]
    
    def get_days_since_last_sync(self, obj):
        if not obj.ldap_last_sync:
            return None
        from django.utils import timezone
        delta = timezone.now() - obj.ldap_last_sync
        return delta.days
    

class CustomUserTechnicalSerializer(serializers.ModelSerializer):
    """
    Serializer technique pour les Network & Identity Managers
    Inclut les informations LDAP et de sécurité
    """
    
    full_name_display = serializers.CharField(source='full_name', read_only=True)
    ldap_group_names = serializers.ListField(source='get_ldap_group_names', read_only=True)
    group_count = serializers.IntegerField(source='get_group_count', read_only=True)
    is_network_manager = serializers.SerializerMethodField()  # ← AJOUTER
    is_network_admin = serializers.SerializerMethodField()    # ← AJOUTER
    
    # Propriétés de mot de passe
    password_expiration_date = serializers.DateTimeField(read_only=True)
    days_until_password_expires = serializers.IntegerField(read_only=True)
    is_password_expired = serializers.BooleanField(read_only=True)
    password_expires_soon = serializers.BooleanField(read_only=True)
    days_since_password_change = serializers.IntegerField(read_only=True)
    
    # Propriétés de compte LDAP
    is_ldap_account_expired = serializers.BooleanField(read_only=True)
    days_since_last_ldap_logon = serializers.IntegerField(read_only=True)
    
    # Statuts
    is_admin = serializers.SerializerMethodField()
    is_network_manager = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name_display',
            'is_active',
            'is_staff',
            'is_superuser',
            'is_admin',
            'is_director',
            'is_human',
            'is_network_manager',
            'is_network_admin',
            
            # Dates de connexion
            'last_login',
            'ldap_last_logon',
            'days_since_last_ldap_logon',
            'date_joined',
            
            # Informations mot de passe
            'ldap_password_last_set',
            'password_expiration_date',
            'days_until_password_expires',
            'is_password_expired',
            'password_expires_soon',
            'days_since_password_change',
            
            # Informations compte
            'ldap_account_expires',
            'is_ldap_account_expired',
            'ldap_created_date',
            'ldap_modified_date',
            'ldap_last_sync',
            
            # Groupes
            'ldap_groups',
            'ldap_group_names',
            'group_count',
        ]
    
    def get_is_admin(self, obj):
        return obj.is_active and (obj.is_staff or obj.is_superuser)
    
    def get_is_network_manager(self, obj):
        return obj.is_network_manager
    
    def get_is_network_admin(self, obj):
        return obj.is_network_manager