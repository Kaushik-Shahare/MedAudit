from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Manually adds creating_session_id column to ehr_patientvisit table"

    def handle(self, *args, **options):
        cursor = connection.cursor()
        
        # Check if the column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='ehr_patientvisit' AND column_name='creating_session_id'
        """)
        column_exists = cursor.fetchone()
        
        if not column_exists:
            self.stdout.write(self.style.WARNING('Column creating_session_id does not exist. Creating it now...'))
            
            # Create the column
            cursor.execute("""
                ALTER TABLE ehr_patientvisit
                ADD COLUMN creating_session_id integer NULL
                REFERENCES ehr_nfcsession(id) 
                ON DELETE SET NULL
            """)
            
            self.stdout.write(self.style.SUCCESS('Successfully added creating_session_id column!'))
        else:
            self.stdout.write(self.style.SUCCESS('Column creating_session_id already exists.'))
