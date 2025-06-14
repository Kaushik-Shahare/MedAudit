from django.core.management.base import BaseCommand
from account.models import UserType, Permission

class Command(BaseCommand):
    help = 'Load initial user types and permissions for each user type.'

    def handle(self, *args, **options):
        # Define user types and their permissions
        usertype_permissions = {
            'Admin': ['manage_users', 'approve_documents', 'view_all_records'],
            'Doctor': ['view_patient_records', 'request_access', 'upload_documents'],
            'Nurse': ['view_patient_records'],
            'Patient': ['view_own_records', 'upload_own_documents'],
        }

        for usertype, perms in usertype_permissions.items():
            usertype_obj, created = UserType.objects.get_or_create(name=usertype)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created user type: {usertype}'))
            for perm in perms:
                perm_obj, _ = Permission.objects.get_or_create(name=perm)
                usertype_obj.permissions.add(perm_obj)
            usertype_obj.save()
            self.stdout.write(self.style.SUCCESS(f'Assigned permissions to {usertype}'))
        self.stdout.write(self.style.SUCCESS('User types and permissions loaded successfully.')) 