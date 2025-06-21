# Patient Visit and NFC Session Requirements

## Overview

This document outlines the requirements and implementation for the Patient Visit creation and NFC Session authentication system.

## Key Requirements

1. **Admin-Only Visit Creation**: 
   - Only Admin users can create a `PatientVisit` for a patient
   - Regular users and doctors cannot create visits directly

2. **NFC Session Requirement**:
   - A valid `NFCSession` (session_id) is required for visit creation
   - The session_id must be passed in the request body or query params (not as a bearer token)

3. **Doctor Access Control**:
   - Doctors cannot create visits directly
   - Doctors can update/view patient documents only after:
     - Generating a valid NFCSession
     - That session must be associated with a visit

## API Usage

### Creating a Visit (Admin only)

```
POST /api/ehr/visits/
```

**Request Body:**
```json
{
  "patient": 1,
  "visit_type": "routine_checkup",
  "reason_for_visit": "Annual checkup",
  "attending_doctor": 3,
  "session_id": 123
}
```

Alternatively, the session_id can be passed as a query parameter:
```
POST /api/ehr/visits/?session_id=123
```

### Doctor Access to Patient Visit Data

1. First, the doctor must generate an NFC session:
```
POST /api/ehr/nfc-session/
```

2. Then, the doctor can access visit data using the session:
```
GET /api/ehr/visits/{visit_id}/
```
The doctor must have an active NFC session associated with this visit.

## Permission Flow

1. Admin creates visit providing a session_id
2. The system associates the NFC session with the visit
3. Doctor can then access the visit data using their NFC session
4. Doctor can update/view patient documents associated with that visit

## Implementation Details

- `perform_create` in `PatientVisitViewSet` enforces admin-only creation and session_id requirement
- The system validates the session and links it to the created visit
- The `PatientVisit` model provides helper methods for permission checking
- All errors are properly raised as DRF exceptions (PermissionDenied, ValidationError)

## Testing

When testing with Postman or similar tools:

1. Ensure the user has proper admin permissions for visit creation
2. Always include a valid session_id in the body or query parameters
3. For doctor access, ensure a session has been created and associated with the visit

## Common Error Responses

- **403 Forbidden**: "Only staff can create visits" - When a doctor or patient tries to create a visit
- **400 Bad Request**: "session_id is required to create a visit" - When session_id is missing
- **400 Bad Request**: "Invalid session ID provided" - When the session_id doesn't exist
