from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class LDAPGroup(models.Model):
    """
    Modèle pour stocker les groupes Active Directory/LDAP.
    """
    name = models.CharField(
        _('group name'),
        max_length=255,
        unique=True,
        help_text=_('Name of the LDAP/AD group (CN value)')
    )
    
    distinguished_name = models.TextField(
        _('distinguished name'),
        unique=True,
        help_text=_('Full DN of the group in LDAP')
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Description of the group')
    )

    human_name = models.CharField(_("human name"), default="Unknown", max_length=50)

    GROUP_TYPE_CHOICE=(("HUMAN",_("human")), ("MACHINE",_("machine")), ("MIXED",_("mixed")), ("UNKNOWN",_("Unknown")))
    
    group_type = models.CharField(_("Group is human"), choices=GROUP_TYPE_CHOICE, default="UNKNOWN")

    # Managers du groupe qui peuvent valider les demandes d'accès
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='managed_ldap_groups',
        verbose_name=_('Group managers'),
        help_text=_('Users who can validate access requests for this group')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('LDAP Group')
        verbose_name_plural = _('LDAP Groups')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def is_manager(self, user):
        """Vérifie si un utilisateur est manager de ce groupe"""
        return self.managers.filter(id=user.id).exists()