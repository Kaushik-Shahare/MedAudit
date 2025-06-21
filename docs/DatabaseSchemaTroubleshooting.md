# Database Schema Troubleshooting for NFC Session Integration

## Issue: Missing `creating_session_id` Column

If you encounter an error like this when creating visits:

```
{
    "status": false,
    "code": 400,
    "message": {
        "error": "Error creating visit: column \"creating_session_id\" of relation \"ehr_patientvisit\" does not exist..."
    }
}
```

This indicates that the database schema does not match the model definition. We've added a `creating_session` field to the `PatientVisit` model, but the corresponding database column hasn't been created yet.

## Solution 1: Run Database Schema Fix Command

We've created a management command to fix database schema issues:

```bash
python manage.py fix_db_schema
```

This command will:
1. Check if the `creating_session_id` column exists in the `ehr_patientvisit` table
2. If not, it will create the column with appropriate foreign key constraints
3. Verify the schema is fixed correctly

## Solution 2: Manual Database Migration

If the above command doesn't work, you can manually run migrations:

```bash
python manage.py makemigrations ehr
python manage.py migrate ehr
```

## Solution 3: Direct SQL

As a last resort, you can manually execute SQL to add the column:

```sql
ALTER TABLE ehr_patientvisit ADD COLUMN creating_session_id integer NULL;
ALTER TABLE ehr_patientvisit ADD CONSTRAINT fk_creating_session 
FOREIGN KEY (creating_session_id) REFERENCES ehr_nfcsession(id) ON DELETE SET NULL;
```

## Verifying the Fix

After applying the fix, you should be able to create visits with the session_token parameter without errors. The system will:

1. Associate the session with the visit through both:
   - The `PatientVisit.creating_session` field
   - The `NFCSession.visit` field
   
2. Log all activities related to the session in the `SessionActivity` model

The patient visit workflow is now fully integrated with the NFC session system, ensuring all patient actions require a valid session token.
