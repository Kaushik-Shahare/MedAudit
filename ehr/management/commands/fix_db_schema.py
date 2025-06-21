from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Fix PatientVisit model database schema issues"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting database schema fix..."))
        
        # Run SQL directly to fix any schema issues
        cursor = connection.cursor()
        
        # Check for creating_session_id column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='ehr_patientvisit' AND column_name='creating_session_id'
        """)
        column_exists = cursor.fetchone()
        
        if not column_exists:
            self.stdout.write(self.style.WARNING("Column creating_session_id missing. Adding it now..."))
            
            # Add column
            cursor.execute("""
                ALTER TABLE ehr_patientvisit
                ADD COLUMN creating_session_id integer NULL
            """)
            
            # Add foreign key constraint
            cursor.execute("""
                ALTER TABLE ehr_patientvisit
                ADD CONSTRAINT fk_creating_session
                FOREIGN KEY (creating_session_id)
                REFERENCES ehr_nfcsession(id)
                ON DELETE SET NULL
            """)
            
            self.stdout.write(self.style.SUCCESS("Column creating_session_id added successfully."))
        else:
            self.stdout.write(self.style.SUCCESS("Column creating_session_id already exists."))
        
        # Look for any other database schema issues
        
        self.stdout.write(self.style.SUCCESS("Database schema fix completed."))
