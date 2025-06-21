# PatientVisit and NFCSession Integration

## Overview

This document outlines the updated requirements and implementation for the PatientVisit creation and NFCSession authentication system.

## Key Requirements

1. **Admin-Only Visit Creation**: 
   - Only Admin users can create a `PatientVisit` for a patient
   - Regular users and doctors cannot create visits directly

2. **NFC Session Requirement**:
   - A valid `NFCSession` is required for visit creation
   - The session can be identified by either:
     - `session_id` (numeric ID) in request body or query params
     - `session_token` (string token) in request body or query params

3. **Doctor Access Control**:
   - Doctors cannot create visits directly
   - Doctors can update/view patient documents only after:
     - Generating a valid NFCSession
     - That session must be associated with a visit

## API Usage

### Creating a Visit (Admin only)

**Using session_token (preferred):**
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
  "session_token": "abcd1234..."
}
```

**Using session_id:**
```json
{
  "patient": 1,
  "visit_type": "routine_checkup",
  "reason_for_visit": "Annual checkup",
  "attending_doctor": 3,
  "session_id": 123
}
```

**Using query parameters:**
```
POST /api/ehr/visits/?session_token=abcd1234...
```
or
```
POST /api/ehr/visits/?session_id=123
```

### Associating an NFC Session with a Visit

```
POST /api/ehr/visits/{visit_id}/add_session/
```

**Request Body:**
```json
{
  "session_token": "abcd1234..."
}
```
or
```json
{
  "session_id": 123
}
```

## Error Handling

The system will perform the following validations:

1. Check if the user is an Admin (staff)
2. Verify that a session identifier is provided
3. Validate the session using both session_token and ID lookup
4. Ensure the session is valid and not expired
5. Verify the session belongs to the patient being visited

Appropriate error messages will be returned for each validation failure.

## Implementation Details

The system uses a dual-lookup approach:
1. First tries to find the session by `session_token`
2. If not found, falls back to finding by the numeric `id`

This ensures flexibility in how clients can integrate with the API while maintaining security.
