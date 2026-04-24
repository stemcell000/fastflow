# authentication/admin.py

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils.html import format_html
from django.utils import timezone
from .models import CustomUser, LDAPGroup
from .forms import CustomUserCreationForm, CustomUserChangeForm

ALLOWED_ASSIGNABLE_GROUPS = ['Editors', 'Moderators']


# ========================================
# LDAP GROUP ADMIN
# ========================================

@admin.register(LDAPGroup)
class LDAPGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'member_count', 'created_at', 'updated_at', 'human_name']
    search_fields = ['name', 'distinguished_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'distinguished_name']
    list_filter = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'distinguished_name', 'human_name', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        count = obj.members.count()
        return format_html(
            '<span style="font-weight: bold; color: #0066cc;">{} membre{}</span>',
            count,
            's' if count > 1 else ''
        )
    member_count.short_description = 'Membres'
    member_count.admin_order_field = 'members__count'


# ========================================
# CUSTOM USER ADMIN
# ========================================

def sync_ldap_users_action(modeladmin, request, queryset):
    """Action pour synchroniser les utilisateurs LDAP depuis l'admin."""
    try:
        call_command('sync_ldap_users')
        messages.success(request, "✅ Utilisateurs LDAP synchronisés avec succès.")
    except Exception as err:
        messages.error(request, f"❌ Erreur lors de la synchronisation LDAP: {err}")

sync_ldap_users_action.short_description = "🔄 Synchroniser avec LDAP"


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    actions = [sync_ldap_users_action]
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    list_display = [
        'username',
        'full_name_display',
        'email',
        'group_count_display',
        'password_status_display',
        'last_login_display',
        'is_active',
        'is_staff',
        'is_human',
    ]
    
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'ldap_groups',
        ('ldap_last_sync', admin.DateFieldListFilter),
        ('ldap_last_logon', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'username',
        'email',
        'first_name',
        'last_name',
        'ldap_groups__name',
        'is_human'
    ]
    
    ordering = ['last_name', 'first_name']
    
    readonly_fields = [
        'date_joined',
        'last_login',
        'ldap_created_date',
        'ldap_modified_date',
        'ldap_last_logon',
        'ldap_password_last_set',
        'ldap_account_expires',
        'ldap_last_sync',
        'password_expiration_display',
        'days_until_expiration_display',
        'password_strength_display',
    ]
    
    filter_horizontal = ['ldap_groups', 'groups', 'user_permissions']
    
    fieldsets = (
        ('Informations de Base', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'avatar', 'is_human')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Groupes LDAP', {
            'fields': ('ldap_groups',),
            'description': 'Groupes Active Directory auxquels l\'utilisateur appartient'
        }),
        ('Dates Django', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
        ('Dates LDAP/Active Directory', {
            'fields': (
                'ldap_created_date',
                'ldap_modified_date',
                'ldap_last_logon',
                'ldap_last_sync',
            ),
            'classes': ('collapse',)
        }),
        ('Mot de Passe LDAP', {
            'fields': (
                'ldap_password_last_set',
                'password_expiration_display',
                'days_until_expiration_display',
                'password_strength_display',
                'ldap_account_expires',
            ),
            'description': 'Informations sur le mot de passe Active Directory'
        }),
    )
    
    add_fieldsets = (
        (None, {
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'avatar',
                'is_active',
                'is_staff',
                'is_superuser',
                'is_human',
                'groups'
            )
        }),
    )
    
    # ========================================
    # QUERYSET PERSONNALISÉ - EXCLURE LES COMPTES $
    # ========================================
    
    def get_queryset(self, request):
        """
        Exclut les comptes de machine (username contenant $).
        Ces comptes sont généralement des comptes de service AD.
        """
        qs = super().get_queryset(request)
        # Exclure les comptes dont le username contient "$"
        return qs.exclude(username__contains='$')
    
    # ========================================
    # MÉTHODES D'AFFICHAGE PERSONNALISÉES
    # ========================================
    
    def full_name_display(self, obj):
        """Affiche le nom complet."""
        return obj.full_name() or '-'
    full_name_display.short_description = 'Nom complet'
    full_name_display.admin_order_field = 'last_name'
    
    def group_count_display(self, obj):
        """Affiche le nombre de groupes LDAP avec badge."""
        count = obj.get_group_count()
        if count == 0:
            return format_html('<span style="color: #999;">0 groupe</span>')
        return format_html(
            '<span style="background-color: #0066cc; color: white; padding: 2px 8px; '
            'border-radius: 10px; font-size: 11px;">{} groupe{}</span>',
            count,
            's' if count > 1 else ''
        )
    group_count_display.short_description = 'Groupes LDAP'
    
    def password_status_display(self, obj):
        """Affiche le statut du mot de passe avec couleurs."""
        if not obj.ldap_password_last_set:
            return format_html('<span style="color: #999;">N/A</span>')
        
        if obj.is_password_expired:
            return format_html(
                '<span style="background-color: #d32f2f; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-weight: bold;">🔴 EXPIRÉ</span>'
            )
        elif obj.password_expires_soon:
            days = obj.days_until_password_expires
            color = '#f57c00' if days <= 7 else '#fbc02d'
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-weight: bold;">⚠️ {} jours</span>',
                color,
                days
            )
        else:
            days = obj.days_until_password_expires
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">✅ {} jours</span>',
                days
            )
    password_status_display.short_description = 'Mot de passe'
    
    def last_login_display(self, obj):
        """Affiche la dernière connexion LDAP."""
        if not obj.ldap_last_logon:
            return format_html('<span style="color: #999;">Jamais</span>')
        
        days_ago = obj.days_since_last_ldap_logon
        if days_ago > 90:
            color = '#d32f2f'  # Rouge si > 90 jours
        elif days_ago > 30:
            color = '#f57c00'  # Orange si > 30 jours
        else:
            color = '#4caf50'  # Vert si < 30 jours
        
        return format_html(
            '<span style="color: {};">{}</span><br>'
            '<small style="color: #999;">il y a {} jours</small>',
            color,
            obj.ldap_last_logon.strftime('%d/%m/%Y'),
            days_ago
        )
    last_login_display.short_description = 'Dernière connexion'
    last_login_display.admin_order_field = 'ldap_last_logon'
    
    def password_expiration_display(self, obj):
        """Affiche la date d'expiration du mot de passe."""
        expiration_date = obj.password_expiration_date
        if not expiration_date:
            return format_html('<span style="color: #999;">N/A</span>')
        
        if obj.is_password_expired:
            return format_html(
                '<span style="color: #d32f2f; font-weight: bold;">{} (EXPIRÉ)</span>',
                expiration_date.strftime('%d/%m/%Y')
            )
        
        return expiration_date.strftime('%d/%m/%Y à %H:%M')
    password_expiration_display.short_description = 'Date d\'expiration'
    
    def days_until_expiration_display(self, obj):
        """Affiche les jours restants avant expiration."""
        days = obj.days_until_password_expires
        if days is None:
            return format_html('<span style="color: #999;">N/A</span>')
        
        if days < 0:
            return format_html(
                '<span style="color: #d32f2f; font-weight: bold;">Expiré depuis {} jours</span>',
                abs(days)
            )
        elif days == 0:
            return format_html(
                '<span style="color: #d32f2f; font-weight: bold;">Expire AUJOURD\'HUI</span>'
            )
        elif days <= 7:
            return format_html(
                '<span style="color: #f57c00; font-weight: bold;">{} jours</span>',
                days
            )
        elif days <= 14:
            return format_html(
                '<span style="color: #fbc02d; font-weight: bold;">{} jours</span>',
                days
            )
        else:
            return format_html('<span style="color: #4caf50;">{} jours</span>', days)
    days_until_expiration_display.short_description = 'Jours restants'
    
    def password_strength_display(self, obj):
        """Affiche une barre de progression pour l'âge du mot de passe."""
        if not obj.ldap_password_last_set:
            return format_html('<span style="color: #999;">N/A</span>')
        
        days_since = obj.days_since_password_change
        days_until = obj.days_until_password_expires or 0
        
        # Calculer le pourcentage
        total_days = 365
        percentage = min(100, (days_since / total_days) * 100)
        
        # Déterminer la couleur
        if percentage >= 95:  # > 95% = rouge
            color = '#d32f2f'
        elif percentage >= 80:  # > 80% = orange
            color = '#f57c00'
        elif percentage >= 60:  # > 60% = jaune
            color = '#fbc02d'
        else:
            color = '#4caf50'  # < 60% = vert
        
        return format_html(
            '<div style="width: 100px; background-color: #e0e0e0; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 10px;"></div>'
            '</div>'
            '<small style="color: #666;">{} jours / 365</small>',
            percentage,
            color,
            days_since
        )
    password_strength_display.short_description = 'Âge du mot de passe'
    
    def get_form(self, request, obj=None, **kwargs):
        """Personnalise le formulaire."""
        form = super().get_form(request, obj, **kwargs)
        
        # Exclure les champs de mot de passe du formulaire d'ajout
        if obj is None:
            form.base_fields.pop('password1', None)
            form.base_fields.pop('password2', None)
        
        return form
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Limite les groupes assignables selon les permissions."""
        if db_field.name == 'groups':
            user_groups = request.user.groups.values_list('name', flat=True)
            
            if request.user.is_superuser:
                kwargs['queryset'] = Group.objects.all()
            elif 'Admin' in user_groups:
                kwargs['queryset'] = Group.objects.filter(name__in=ALLOWED_ASSIGNABLE_GROUPS)
            else:
                kwargs['queryset'] = Group.objects.none()
        
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# ========================================
# CONFIGURATION SUPPLÉMENTAIRE
# ========================================

# Personnaliser le titre de l'admin
admin.site.site_header = "Administration Fellowship"
admin.site.site_title = "Fellowship Admin"
admin.site.index_title = "Gestion des utilisateurs et groupes LDAP"
