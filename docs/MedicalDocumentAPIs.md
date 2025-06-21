# Medical Document APIs

This document outlines the available API endpoints for managing medical documents within the EHR system. All endpoints require a valid NFC session token and are restricted to medical staff (doctors and admins).

## Authentication and Authorization

- All endpoints require JWT authentication (Bearer token)
- All endpoints require a valid NFC session token 
- Access is restricted to doctors and admin users
- Doctors can only access records for patients they are attending or have an active NFC session for

## Common Request Pattern

All document creation APIs follow this general pattern:

```json
{
  "visit": 123,  // ID of the PatientVisit
  "session_token": "abc123...",  // Valid NFC session token
  ... // Document-specific fields
}
```

## Vital Signs API

### Endpoints

- **GET** `/api/ehr/vital-signs/` - List vital signs (filtered by permissions)
- **POST** `/api/ehr/vital-signs/` - Create a new vital signs record
- **GET** `/api/ehr/vital-signs/{id}/` - Retrieve a specific vital signs record
- **PUT/PATCH** `/api/ehr/vital-signs/{id}/` - Update a vital signs record
- **DELETE** `/api/ehr/vital-signs/{id}/` - Delete a vital signs record
- **GET** `/api/ehr/vital-signs/by_visit/?visit_id={id}` - Get all vital signs for a specific visit

### Sample Request

```json
{
  "visit": 123,
  "session_token": "abc123...",
  "temperature": 37.2,
  "temperature_unit": "celsius",
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 72,
  "respiratory_rate": 16,
  "oxygen_saturation": 98.5,
  "height": 175,
  "height_unit": "cm",
  "weight": 70,
  "weight_unit": "kg",
  "notes": "Patient appears healthy"
}
```

### Sample Response

```json
{
  "id": 1,
  "visit": 123,
  "temperature": 37.2,
  "temperature_unit": "celsius",
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 72,
  "respiratory_rate": 16,
  "oxygen_saturation": 98.5,
  "height": 175,
  "height_unit": "cm",
  "weight": 70,
  "weight_unit": "kg",
  "bmi": 22.86,
  "notes": "Patient appears healthy",
  "recorded_at": "2025-06-21T14:30:00Z",
  "recorded_by": 456,
  "recorded_by_name": "Dr. Smith"
}
```

## Diagnosis API

### Endpoints

- **GET** `/api/ehr/diagnoses/` - List diagnoses (filtered by permissions)
- **POST** `/api/ehr/diagnoses/` - Create a new diagnosis record
- **GET** `/api/ehr/diagnoses/{id}/` - Retrieve a specific diagnosis
- **PUT/PATCH** `/api/ehr/diagnoses/{id}/` - Update a diagnosis
- **DELETE** `/api/ehr/diagnoses/{id}/` - Delete a diagnosis
- **GET** `/api/ehr/diagnoses/by_visit/?visit_id={id}` - Get all diagnoses for a specific visit

### Sample Request

```json
{
  "visit": 123,
  "session_token": "abc123...",
  "condition_name": "Hypertension",
  "icd_code": "I10",
  "severity": "moderate",
  "status": "chronic",
  "notes": "Patient has a family history of hypertension",
  "treatment_plan": "Prescribed lisinopril 10mg daily. Follow-up in 3 months."
}
```

### Sample Response

```json
{
  "id": 1,
  "visit": 123,
  "condition_name": "Hypertension",
  "icd_code": "I10",
  "diagnosis_date": "2025-06-21",
  "severity": "moderate",
  "status": "chronic",
  "notes": "Patient has a family history of hypertension",
  "treatment_plan": "Prescribed lisinopril 10mg daily. Follow-up in 3 months.",
  "diagnosed_by": 456,
  "diagnosed_by_name": "Dr. Smith",
  "created_at": "2025-06-21T14:30:00Z",
  "updated_at": "2025-06-21T14:30:00Z"
}
```

## Lab Result API

### Endpoints

- **GET** `/api/ehr/lab-results/` - List lab results (filtered by permissions)
- **POST** `/api/ehr/lab-results/` - Create a new lab result
- **GET** `/api/ehr/lab-results/{id}/` - Retrieve a specific lab result
- **PUT/PATCH** `/api/ehr/lab-results/{id}/` - Update a lab result
- **DELETE** `/api/ehr/lab-results/{id}/` - Delete a lab result
- **GET** `/api/ehr/lab-results/by_visit/?visit_id={id}` - Get all lab results for a specific visit

### Sample Request

```json
{
  "visit": 123,
  "session_token": "abc123...",
  "test_name": "Complete Blood Count (CBC)",
  "test_date": "2025-06-21T10:00:00Z",
  "result": "Normal",
  "normal_range": "4.5-11.0 x10^9/L",
  "units": "x10^9/L",
  "interpretation": "WBC, RBC, and platelet counts all within normal ranges.",
  "performed_by": "LabCorp"
}
```

### Sample Response

```json
{
  "id": 1,
  "visit": 123,
  "test_name": "Complete Blood Count (CBC)",
  "test_date": "2025-06-21T10:00:00Z",
  "result": "Normal",
  "normal_range": "4.5-11.0 x10^9/L",
  "units": "x10^9/L",
  "interpretation": "WBC, RBC, and platelet counts all within normal ranges.",
  "performed_by": "LabCorp",
  "ordered_by": 456,
  "ordered_by_name": "Dr. Smith",
  "created_at": "2025-06-21T14:30:00Z",
  "updated_at": "2025-06-21T14:30:00Z"
}
```

## Prescription API

### Endpoints

- **GET** `/api/ehr/prescriptions/` - List prescriptions (filtered by permissions)
- **POST** `/api/ehr/prescriptions/` - Create a new prescription
- **GET** `/api/ehr/prescriptions/{id}/` - Retrieve a specific prescription
- **PUT/PATCH** `/api/ehr/prescriptions/{id}/` - Update a prescription
- **DELETE** `/api/ehr/prescriptions/{id}/` - Delete a prescription
- **GET** `/api/ehr/prescriptions/by_visit/?visit_id={id}` - Get all prescriptions for a specific visit

### Sample Request

```json
{
  "visit": 123,
  "session_token": "abc123...",
  "medication_name": "Lisinopril",
  "dosage": "10mg",
  "frequency": "Once daily",
  "duration": "90 days",
  "start_date": "2025-06-21",
  "end_date": "2025-09-19",
  "pharmacy": "MedPlus Pharmacy",
  "instructions": "Take in the morning with food",
  "reason": "Treatment for hypertension"
}
```

### Sample Response

```json
{
  "id": 1,
  "visit": 123,
  "medication_name": "Lisinopril",
  "dosage": "10mg",
  "frequency": "Once daily",
  "duration": "90 days",
  "start_date": "2025-06-21",
  "end_date": "2025-09-19",
  "pharmacy": "MedPlus Pharmacy",
  "instructions": "Take in the morning with food",
  "reason": "Treatment for hypertension",
  "prescribed_by": 456,
  "prescribed_by_name": "Dr. Smith",
  "created_at": "2025-06-21T14:30:00Z",
  "updated_at": "2025-06-21T14:30:00Z"
}
```

## Error Responses

### Invalid Session Token

```json
{
  "session_token": "This session has expired, please generate a new one by tapping the NFC card again",
  "error_code": "expired_session"
}
```

### Permission Denied

```json
{
  "error": "You do not have permission to perform this action"
}
```

### Visit Not Found

```json
{
  "error": "Visit not found"
}
```

## Automatic Charges

Creating each type of medical document automatically generates the appropriate charge for the visit:

- **Vital Signs**: $25.00 charge for vital signs recording (if first record)
- **Diagnosis**: $50.00-$125.00 charge based on severity (mild, moderate, severe)
- **Lab Result**: $45.00-$350.00 charge based on test type
- **Prescription**: $25.00 or calculated based on medication duration

All charges are automatically added to the visit's total amount and viewable through the Visit Charges API.
