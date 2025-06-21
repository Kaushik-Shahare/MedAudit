# PatientVisit and NFCSession Integration

## Overview

This document outlines the updated requirements and implementation for the PatientVisit creation and NFCSession authentication system.

## Key Requirements

1. **Admin-Only Visit Creation**: 
   - Only Admin users can create a `PatientVisit` for a patient
   - Regular users and doctors cannot create visits directly

2. **NFC Session Token Requirement**:
   - A valid `NFCSession` is required for visit creation
   - Only `session_token` (string token) is accepted in request body or query params
   - The system will use the token to find the session, then use the session's ID internally

3. **Doctor Access Control**:
   - Doctors cannot create visits directly
   - Doctors can update/view patient documents only after:
     - Generating a valid NFCSession
     - That session must be associated with a visit

## API Usage

### Creating a Visit (Admin only)

**Using session_token in request body:**
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

**Using query parameters:**
```
POST /api/ehr/visits/?session_token=abcd1234...
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

## Error Handling

The system will perform the following validations:

1. Check if the user is an Admin (staff)
2. Verify that a session token is provided
3. Validate the session using the token
4. Ensure the session is valid and not expired
5. Verify the session belongs to the patient being visited

Appropriate error messages will be returned for each validation failure.

## Implementation Details

The implementation now:
1. Only accepts `session_token` as input
2. No longer falls back to ID-based lookups
3. Uses the token to find the session
4. Associates the visit with the found session's ID internally

This ensures consistent token-based authentication while maintaining numerical ID references internally.
