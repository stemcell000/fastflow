from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create Network & Identity Manager group with appropriate permissions"
    
    def handle(self, *args, **options):
        """
        Méthode principale appelée lors de l'exécution de la commande
        """
        self.stdout.write(self.style.WARNING('Creating Network & Identity Manager group...'))
        
        # Créer le groupe
        group, created = Group.objects.get_or_create(name='Network & Identity Manager')
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Group created: {group.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'ℹ️  Group already exists: {group.name}'))
        
        # Ajouter des permissions spécifiques
        permissions = Permission.objects.filter(
            codename__in=[
                'view_customuser',
                'change_customuser',
                'view_ldapgroup',
                'change_ldapgroup',
            ]
        )
        
        # Vérifier que les permissions existent
        permission_count = permissions.count()
        if permission_count == 0:
            self.stdout.write(self.style.ERROR('❌ No permissions found!'))
            return
        
        # Assigner les permissions au groupe
        group.permissions.set(permissions)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Permissions added: {permission_count}'))
        
        # Afficher les détails
        self.stdout.write('\n📋 Group details:')
        self.stdout.write(f'   Name: {group.name}')
        self.stdout.write(f'   ID: {group.id}')
        self.stdout.write(f'   Permissions:')
        for perm in group.permissions.all():
            self.stdout.write(f'      - {perm.codename} ({perm.name})')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Network & Identity Manager group configured successfully!'))