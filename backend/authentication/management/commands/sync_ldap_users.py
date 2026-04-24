import ldap
import core.settings
from django.core.management.base import BaseCommand
from authentication.models import CustomUser, LDAPGroup
from django.conf import settings
from datetime import datetime, timezone, timedelta
import re

class Command(BaseCommand):
    help = "Sync users from LDAP with dates and group membership"

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-dates',
            action='store_true',
            help='Show date information for debugging',
        )
        parser.add_argument(
            '--show-groups',
            action='store_true',
            help='Show group membership for debugging',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )

    def convert_ad_timestamp(self, ad_timestamp):
        """Convertit un timestamp Active Directory en datetime Python."""
        try:
            if isinstance(ad_timestamp, bytes):
                ad_timestamp = int(ad_timestamp.decode())
            if isinstance(ad_timestamp, str):
                ad_timestamp = int(ad_timestamp)
            
            if ad_timestamp == 0 or ad_timestamp == 9223372036854775807:
                return None
            
            unix_timestamp = (ad_timestamp - 116444736000000000) / 10000000
            return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        
        except (ValueError, TypeError, OSError):
            return None

    def convert_generalized_time(self, gt_string):
        """Convertit un GeneralizedTime LDAP en datetime Python."""
        try:
            if isinstance(gt_string, bytes):
                gt_string = gt_string.decode('utf-8')
            
            gt_string = gt_string.rstrip('Z').split('.')[0]
            return datetime.strptime(gt_string, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        
        except (ValueError, AttributeError):
            return None

    def get_ldap_value(self, entry, key):
        """Récupère une valeur texte depuis LDAP."""
        return entry.get(key, [b""])[0].decode(errors="ignore").strip() if entry.get(key) else None

    def get_ldap_date(self, entry, key, is_filetime=True):
        """Récupère et convertit une date depuis LDAP."""
        value = entry.get(key)
        if not value or not value[0]:
            return None
        
        if is_filetime:
            return self.convert_ad_timestamp(value[0])
        else:
            return self.convert_generalized_time(value[0])

    def extract_cn_from_dn(self, dn):
        """
        Extrait le CN (Common Name) d'un Distinguished Name.
        
        Exemple:
        DN: "CN=IT_Team,OU=Groups,DC=institut-vision,DC=local"
        Retourne: "IT_Team"
        """
        match = re.match(r'CN=([^,]+)', dn, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def parse_memberof(self, entry):
        """
        Parse l'attribut memberOf pour extraire les groupes.
        
        Args:
            entry: dict - entrée LDAP
            
        Returns:
            list: Liste de tuples (cn, dn) des groupes
        """
        memberof_values = entry.get('memberOf', [])
        groups = []
        
        for member_dn in memberof_values:
            if isinstance(member_dn, bytes):
                member_dn = member_dn.decode('utf-8', errors='ignore')
            
            # Extraire le CN du DN
            cn = self.extract_cn_from_dn(member_dn)
            if cn:
                groups.append((cn, member_dn))
        
        return groups

    def sync_ldap_groups(self, groups_data):
        """
        Synchronise les groupes LDAP dans la base de données.
        
        Args:
            groups_data: list - Liste de tuples (cn, dn)
            
        Returns:
            list: Liste des objets LDAPGroup créés/mis à jour
        """
        ldap_group_objects = []
        
        for cn, dn in groups_data:
            group, created = LDAPGroup.objects.get_or_create(
                distinguished_name=dn,
                defaults={'name': cn}
            )
            
            # Mettre à jour le nom si nécessaire
            if group.name != cn:
                group.name = cn
                group.save(update_fields=['name', 'updated_at'])
            
            ldap_group_objects.append(group)
        
        return ldap_group_objects

    def handle(self, *args, **kwargs):
        show_dates = kwargs.get('show_dates', False)
        show_groups = kwargs.get('show_groups', False)
        dry_run = kwargs.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made in the database"))
        
        try:
            ldap_conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            ldap_conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN, settings.AUTH_LDAP_BIND_PASSWORD)
            self.stdout.write(self.style.SUCCESS("✅ LDAP connection established"))
        except ldap.LDAPError as e:
            self.stdout.write(self.style.ERROR(f"❌ LDAP connection failed: {e}"))
            return

        search_base = "OU=IDV - Tier 1 and 2,DC=institut-vision,DC=local"
        search_filter = "(&(objectClass=user)(objectCategory=person))"
        
        # Ajouter memberOf aux attributs à récupérer
        attributes = [
            "sAMAccountName", 
            "mail", 
            "givenName", 
            "sn", 
            "distinguishedName",
            "whenCreated",
            "whenChanged",
            "lastLogon",
            "lastLogonTimestamp",
            "pwdLastSet",
            "accountExpires",
            "badPasswordTime",
            "memberOf",  # 🔥 Groupes LDAP
        ]

        ldap_conn.set_option(ldap.OPT_SIZELIMIT, 5000)

        try:
            result = ldap_conn.search_s(search_base, ldap.SCOPE_SUBTREE, search_filter, attributes)
            self.stdout.write(self.style.SUCCESS(f"✅ Found {len(result)} entries in LDAP"))
        except ldap.LDAPError as e:
            self.stdout.write(self.style.ERROR(f"❌ LDAP search failed: {e}"))
            ldap_conn.unbind_s()
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        groups_synced = 0

        for dn, entry in result:
            username = self.get_ldap_value(entry, "sAMAccountName")
            
            if not username:
                skipped_count += 1
                continue

            email = self.get_ldap_value(entry, "mail") or ""
            first_name = self.get_ldap_value(entry, "givenName") or ""
            last_name = self.get_ldap_value(entry, "sn") or ""
            distinguished_name = entry.get("distinguishedName", [b""])[0].decode() if entry.get("distinguishedName") else ""

            # Récupération des dates
            when_created = self.get_ldap_date(entry, "whenCreated", is_filetime=False)
            when_changed = self.get_ldap_date(entry, "whenChanged", is_filetime=False)
            last_logon = self.get_ldap_date(entry, "lastLogon", is_filetime=True)
            last_logon_timestamp = self.get_ldap_date(entry, "lastLogonTimestamp", is_filetime=True)
            pwd_last_set = self.get_ldap_date(entry, "pwdLastSet", is_filetime=True)
            account_expires = self.get_ldap_date(entry, "accountExpires", is_filetime=True)

            # 🔥 Extraction des groupes
            groups_data = self.parse_memberof(entry)

            is_disabled = "OU=Disabled" in distinguished_name

            if show_dates or show_groups:
                self.stdout.write(self.style.NOTICE(f"\n{'='*70}"))
                self.stdout.write(self.style.NOTICE(f"👤 User: {username} ({first_name} {last_name})"))
                self.stdout.write(self.style.NOTICE(f"📧 Email: {email}"))
                
                if show_dates:
                    self.stdout.write(self.style.NOTICE(f"\n📅 Date Information:"))
                    self.stdout.write(self.style.NOTICE(f"   Created:            {when_created or 'N/A'}"))
                    self.stdout.write(self.style.NOTICE(f"   Last Modified:      {when_changed or 'N/A'}"))
                    self.stdout.write(self.style.NOTICE(f"   Last Logon:         {last_logon_timestamp or last_logon or 'N/A'}"))
                    self.stdout.write(self.style.NOTICE(f"   Password Set:       {pwd_last_set or 'N/A'}"))
                    
                    if pwd_last_set:
                        expiration = pwd_last_set + timedelta(days=365)
                        days_until = (expiration - datetime.now(timezone.utc)).days
                        self.stdout.write(self.style.NOTICE(f"   Password Expires:   {expiration} ({days_until} days)"))
                
                if show_groups:
                    self.stdout.write(self.style.NOTICE(f"\n👥 Groups ({len(groups_data)}):"))
                    for cn, group_dn in groups_data:
                        self.stdout.write(self.style.NOTICE(f"   - {cn}"))
                
                self.stdout.write(self.style.NOTICE(f"{'='*70}\n"))

            # Skip service accounts
            if "OU=Services" in distinguished_name:
                self.stdout.write(self.style.WARNING(f"⏭️  Skipping service account: {username}"))
                skipped_count += 1
                continue

            # Skip if username already exists (only for creation, not update)
            if CustomUser.objects.filter(username__iexact=username).exists():
                self.stdout.write(self.style.WARNING(f"⏭️  Skipping existing user: {username}"))
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(self.style.NOTICE(f"[DRY RUN] Would create/update: {username} with {len(groups_data)} groups"))
                continue

            try:
                last_login = last_logon_timestamp or last_logon
                
                user, created = CustomUser.objects.update_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": not is_disabled,
                        "date_joined": when_created or datetime.now(timezone.utc),
                        "ldap_created_date": when_created,
                        "ldap_modified_date": when_changed,
                        "ldap_last_logon": last_login,
                        "ldap_password_last_set": pwd_last_set,
                        "ldap_account_expires": account_expires,
                    },
                )

                # 🔥 Synchroniser les groupes
                if groups_data:
                    ldap_group_objects = self.sync_ldap_groups(groups_data)
                    user.ldap_groups.set(ldap_group_objects)
                    groups_synced += len(ldap_group_objects)

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ Created: {username} ({first_name} {last_name}) - {len(groups_data)} groups"
                    ))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"🔄 Updated: {username} ({first_name} {last_name}) - {len(groups_data)} groups"
                    ))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing {username}: {e}"))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        ldap_conn.unbind_s()
        
        self.stdout.write(self.style.SUCCESS(f"\n{'='*70}"))
        self.stdout.write(self.style.SUCCESS(f"📊 SYNCHRONIZATION SUMMARY"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Created:  {created_count} users"))
        self.stdout.write(self.style.SUCCESS(f"🔄 Updated:  {updated_count} users"))
        self.stdout.write(self.style.SUCCESS(f"⏭️  Skipped:  {skipped_count} users"))
        self.stdout.write(self.style.SUCCESS(f"👥 Groups:   {groups_synced} group memberships synced"))
        self.stdout.write(self.style.SUCCESS(f"📝 Total:    {len(result)} LDAP entries"))
        self.stdout.write(self.style.SUCCESS(f"{'='*70}\n"))
