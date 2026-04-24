from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta


class CustomUser(AbstractUser):
    """
    Modèle utilisateur personnalisé avec champs LDAP et rôles étendus
    """
    # Avatar
    avatar = models.ImageField(
        _('avatar'),
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text=_('User profile picture')
    )

    # Humain vs. Machine
    is_human = models.BooleanField(
        _('human account'),
        blank=True,
        null=True,
        default=True,
        help_text=_('Designates whether this is a human user account (vs team/service/technical account)')
    )
    
    # Catégorie
    category = models.ForeignKey(
        'authentication.CustomUserCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_user_set',
        verbose_name=_('User category')
    )
    
    # Rôle Director
    is_director = models.BooleanField(
        _('director status'),
        default=False,
        help_text=_('Designates whether the user is a director who can validate all access requests')
    )
    
    # Champs LDAP - Dates
    ldap_created_date = models.DateTimeField(
        _('LDAP creation date'),
        null=True,
        blank=True,
        help_text=_('When the account was created in Active Directory')
    )
    
    ldap_modified_date = models.DateTimeField(
        _('LDAP modification date'),
        null=True,
        blank=True,
        help_text=_('Last time the account was modified in Active Directory')
    )
    
    ldap_last_logon = models.DateTimeField(
        _('LDAP last logon'),
        null=True,
        blank=True,
        help_text=_('Last logon time from Active Directory')
    )
    
    ldap_password_last_set = models.DateTimeField(
        _('LDAP password last set'),
        null=True,
        blank=True,
        help_text=_('When the password was last changed in Active Directory')
    )
    
    ldap_account_expires = models.DateTimeField(
        _('LDAP account expiration'),
        null=True,
        blank=True,
        help_text=_('Account expiration date from Active Directory')
    )
    
    ldap_last_sync = models.DateTimeField(
        _('Last LDAP sync'),
        null=True,
        blank=True,
        help_text=_('Last time this user was synchronized with LDAP')
    )
    
    # Groupes LDAP
    ldap_groups = models.ManyToManyField(
        'authentication.LDAPGroup',
        blank=True,
        related_name='members',
        verbose_name=_('LDAP groups')
    )
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return self.username
    
    def full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    # ===========================
    # PROPRIÉTÉS LDAP - MOT DE PASSE
    # ===========================
    
    @property
    def password_expiration_date(self):
        """Calcule la date d'expiration du mot de passe (90 jours après changement)"""
        if not self.ldap_password_last_set:
            return None
        return self.ldap_password_last_set + timedelta(days=90)
    
    @property
    def days_until_password_expires(self):
        """Nombre de jours avant expiration du mot de passe"""
        if not self.password_expiration_date:
            return None
        delta = self.password_expiration_date - timezone.now()
        return max(0, delta.days)
    
    @property
    def is_password_expired(self):
        """Vérifie si le mot de passe est expiré"""
        if not self.password_expiration_date:
            return False
        return timezone.now() > self.password_expiration_date
    
    @property
    def password_expires_soon(self):
        """Vérifie si le mot de passe expire dans les 14 jours"""
        if not self.days_until_password_expires:
            return False
        return 0 <= self.days_until_password_expires <= 14
    
    # ===========================
    # PROPRIÉTÉS LDAP - COMPTE
    # ===========================
    
    @property
    def is_ldap_account_expired(self):
        """Vérifie si le compte LDAP est expiré"""
        if not self.ldap_account_expires:
            return False
        return timezone.now() > self.ldap_account_expires
    
    @property
    def days_since_last_ldap_logon(self):
        """Nombre de jours depuis la dernière connexion LDAP"""
        if not self.ldap_last_logon:
            return None
        delta = timezone.now() - self.ldap_last_logon
        return delta.days
    
    @property
    def days_since_password_change(self):
        """Nombre de jours depuis le dernier changement de mot de passe"""
        if not self.ldap_password_last_set:
            return None
        delta = timezone.now() - self.ldap_password_last_set
        return delta.days
    
    # ===========================
    # PROPRIÉTÉS COMPTE ADMIN
    # ===========================

    @property
    def is_network_manager(self):
        """Vérifie si l'utilisateur est Network & Identity Manager"""
        return self.groups.filter(name='Network & Identity Manager').exists() or self.is_staff
    
    @property
    def is_network_manager(self):
        """
        Vérifie si l'utilisateur est Network & Identity Manager
        Donne accès à la vue technique des utilisateurs
        """
        return (
            self.is_staff or 
            self.groups.filter(name='Network & Identity Manager').exists()
        )
    
    # Alias pour compatibilité
    @property
    def is_network_admin(self):
        """Alias pour is_network_manager"""
        return self.is_network_manager
    
    # ===========================
    # MÉTHODES GROUPES
    # ===========================
    
    def get_ldap_group_names(self):
        """Retourne la liste des noms de groupes LDAP"""
        return list(self.ldap_groups.values_list('name', flat=True))
    
    def get_group_count(self):
        """Retourne le nombre de groupes LDAP"""
        return self.ldap_groups.count()