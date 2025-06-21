# Troubleshooting API Issues in the MedAudit System

## Common API Error Codes

### 1. Session-Related Errors

- **inactive_session**: The session has been manually invalidated or revoked
- **expired_session**: The session has expired due to timeout (default 4 hours)
- **invalid_token**: The provided session token does not exist in the system

### 2. Permission Errors

- **403 Forbidden**: User doesn't have permission for the requested action
- **401 Unauthorized**: Authentication is required (missing or invalid token)

### 3. Data Validation Errors

- **400 Bad Request**: Data validation errors (missing fields, wrong format, etc.)

## Common Issues and Solutions

### Patient Visit Creation (500 Error)

If you're receiving a 500 error when creating a patient visit, check:

1. The `session_token` is valid and not expired
2. The `patient` ID matches the patient associated with the session
3. The user is a staff member (admin)
4. All required fields are provided (patient, visit_type)

Example of a correct request:

```bash
curl --location 'http://localhost:8000/api/ehr/patient-visits/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
  "patient": 10,
  "attending_doctor": 2,
  "visit_type": "specialist_consultation",
  "reason_for_visit": "Cardiology consultation",
  "session_token": "VALID_SESSION_TOKEN"
}'
```

### Session Validation

To check if a session is valid before using it:

```bash
curl --location 'http://localhost:8000/api/ehr/patient-visits/validate_session/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
  "session_token": "YOUR_SESSION_TOKEN"
}'
```

### Extending a Session

If a session is about to expire, you can extend it:

```bash
curl --location 'http://localhost:8000/api/ehr/patient-visits/extend_session/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer YOUR_JWT_TOKEN' \
--data '{
  "session_token": "YOUR_SESSION_TOKEN",
  "hours": 2  # Optional, defaults to 4 hours
}'
```

## Flow for Working with Patient Data

1. **Generate NFC Session**: Tap the patient's NFC card to generate a session token
2. **Validate Session** (Optional): Verify that the session is valid
3. **Create/Update Patient Data**: Use the session token for all patient-related operations
4. **Monitor Session Validity**: Check for expired_session error codes and generate new sessions as needed

## Logs to Check for Troubleshooting

1. Django request logs: `/Users/kaushik/Projects/Hackathon/MedAudit/logs/app.log`
2. Request logs: `/Users/kaushik/Projects/Hackathon/MedAudit/logs/requests/requests.log`

## Session Activity Tracking

You can view the history of session activities:

```bash
# All activities (filtered by user permissions)
GET /api/ehr/session-activities/

# Activities for a specific session
GET /api/ehr/session-activities/by_session/?session_token=XYZ

# Activities for a specific visit
GET /api/ehr/session-activities/by_visit/?visit_id=123
```
