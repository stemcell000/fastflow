from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserCategory(models.Model):
    """
    Catégories d'utilisateurs pour classification
    """
    name = models.CharField(
        _('category name'),
        max_length=100,
        unique=True,
        default="user"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = _('User Category')
        verbose_name_plural = _('User Categories')
        ordering = ['name']
    
    def __str__(self):
        return self.name