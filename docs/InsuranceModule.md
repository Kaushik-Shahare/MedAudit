# Insurance Module Documentation

## Overview

The Insurance Module in MedAudit system allows doctors and administrators to create and manage insurance forms linked to patient visits. It supports different types of insurance policies, including cashless options, and features AI-based approval capabilities.

## Models

### InsuranceType

Represents different types of insurance policies available in the system.

- **name**: Name of the insurance policy type
- **description**: Detailed description of the policy
- **is_cashless**: Whether this type of insurance supports cashless claims
- **coverage_percentage**: Percentage of costs covered by insurance
- **max_coverage_amount**: Maximum coverage amount
- **waiting_period_days**: Waiting period before coverage becomes active
- **requires_pre_authorization**: Whether pre-authorization is required for claims

### InsurancePolicy

Links insurance policies to specific patients.

- **policy_number**: Unique identifier for the policy
- **patient**: The patient who owns this policy
- **insurance_type**: The type of insurance policy
- **provider**: Insurance company providing the policy
- **issuer**: Entity that issued the policy
- **valid_from/valid_till**: Validity dates for the policy
- **sum_insured**: Total insured amount
- **premium_amount**: Premium paid by the patient
- **is_active**: Whether this policy is currently active

### InsuranceForm

Represents an insurance claim form linked to a patient visit. The form supports both regular and cashless claims with pre-authorization workflows.

#### Basic Information
- **visit**: The patient visit this insurance form is for
- **policy**: The insurance policy being claimed
- **created_by**: User who created this form (doctor or admin)
- **reference_number**: Unique reference number for this claim
- **status**: Current status of the form (draft, submitted, approved, etc.)
- **is_cashless_claim**: Whether this is a cashless claim
- **provider_type**: Whether hospital is network or non-network

#### Patient Condition and Medical Details
- **diagnosis**: Diagnosis description
- **icd_code**: ICD-10 diagnosis code
- **presenting_complaints**: Patient's presenting complaints with duration
- **past_history**: Relevant past medical/surgical history
- **treatment_description**: Description of treatment provided
- **clinical_findings**: Clinical findings from examination
- **proposed_line_of_treatment**: Proposed line of treatment
- **investigation_details**: Investigation reports supporting diagnosis
- **route_of_drug_administration**: Route of drug administration

#### Hospital and Treatment Details
- **treatment_type**: Type of treatment (emergency, planned, maternity, etc.)
- **hospitalization_type**: Type of hospitalization (single room, shared, ICU, etc.)
- **expected_days_of_stay**: Expected duration of hospitalization
- **admission_date**: Date of admission
- **expected_discharge_date**: Expected date of discharge
- **treating_doctor**: Doctor treating the patient
- **doctor_registration_number**: Registration number of treating doctor
- **is_injury_related**: Whether condition is related to an injury
- **injury_details**: Details of injury if applicable
- **is_maternity_related**: Whether claim is for maternity
- **date_of_delivery**: Date of delivery if applicable

#### Financial Details
- **claim_amount**: Total amount being claimed
- **room_rent_per_day**: Room rent per day
- **icu_charges_per_day**: ICU charges per day if applicable
- **ot_charges**: Operation theatre charges
- **professional_fees**: Professional fees for doctors
- **medicine_consumables**: Cost of medicines and consumables
- **investigation_charges**: Cost of investigations
- **approved_amount**: Amount approved by insurance company

#### Pre-authorization Details
- **pre_authorization_reference**: Reference number for pre-authorization
- **pre_authorization_date**: Date when pre-authorization was requested
- **pre_authorized_amount**: Amount pre-authorized by insurance company
- **pre_auth_remarks**: Insurance company's remarks on pre-authorization

#### AI Approval
- **is_ai_approved**: Whether this claim was approved by AI
- **ai_confidence_score**: Confidence score from AI analysis
- **ai_analysis**: Detailed analysis data from AI
- **ai_processing_date**: Date when AI processed this claim

#### Enhancement Details
- **enhancement_requested**: Whether enhancement has been requested
- **enhancement_amount**: Amount of enhancement requested
- **enhancement_reason**: Reason for enhancement request

#### Process Dates
- **submission_date**: Date when form was submitted
- **approval_date**: Date when form was approved
- **rejection_reason**: Reason for rejection if applicable

## API Endpoints

### Insurance Types

- `GET /api/insurance/types/`: List all insurance types
- `POST /api/insurance/types/`: Create a new insurance type (admin only)
- `GET /api/insurance/types/{id}/`: Get details of a specific insurance type
- `PUT/PATCH /api/insurance/types/{id}/`: Update an insurance type (admin only)
- `DELETE /api/insurance/types/{id}/`: Delete an insurance type (admin only)

### Insurance Policies

- `GET /api/insurance/policies/`: List insurance policies (filtered by user role)
- `POST /api/insurance/policies/`: Create a new insurance policy (admin/doctor only)
- `GET /api/insurance/policies/{id}/`: Get details of a specific policy
- `PUT/PATCH /api/insurance/policies/{id}/`: Update a policy (admin/doctor only)
- `DELETE /api/insurance/policies/{id}/`: Delete a policy (admin only)
- `GET /api/insurance/policies/active/`: List only active insurance policies
- `GET /api/insurance/policies/patient_policies/?patient_id=X`: Get policies for a specific patient

### Insurance Forms

- `GET /api/insurance/forms/`: List insurance forms (filtered by user role)
  - Optional query parameters: `status`, `is_cashless`, `treatment_type`
- `POST /api/insurance/forms/`: Create a new insurance form
  - Add `auto_populate: true` in the request body to automatically fill form data from EHR
- `GET /api/insurance/forms/{id}/`: Get details of a specific form
- `PUT/PATCH /api/insurance/forms/{id}/`: Update an insurance form
- `DELETE /api/insurance/forms/{id}/`: Delete an insurance form
- `POST /api/insurance/forms/{id}/submit/`: Submit an insurance form for processing
- `POST /api/insurance/forms/{id}/approve/`: Approve an insurance form (admin/superadmin only)
- `POST /api/insurance/forms/{id}/reject/`: Reject an insurance form (admin/superadmin only)
- `POST /api/insurance/forms/{id}/ai_approval/`: Process AI approval for a form (admin/superadmin only)
- `POST /api/insurance/forms/{id}/request_enhancement/`: Request enhancement for a cashless claim (doctor/admin only)
- `POST /api/insurance/forms/{id}/finalize_claim/`: Finalize a cashless claim after treatment (doctor/admin only)
- `POST /api/insurance/forms/{id}/mark_payment_completed/`: Mark payment as completed (admin/superadmin only)
- `POST /api/insurance/forms/{id}/update_from_visit_data/`: Update form with latest visit data from EHR
- `POST /api/insurance/forms/auto_create_from_visit/`: Automatically create form from visit data
  - Requires: `visit_id`, `policy_id`, and optionally `is_cashless`
- `GET /api/insurance/forms/visit_forms/?visit_id=X`: Get forms for a specific visit
- `GET /api/insurance/forms/cashless_claims/`: Get only cashless insurance claims
  - Optional query parameter: `status` to filter by status
- `GET /api/insurance/forms/pending_preauth/`: Get all pending pre-authorization forms
- `GET /api/insurance/forms/enhancement_requests/`: Get all forms with enhancement requests

## Permissions

- **Admins**: Full access to all insurance-related data and operations
- **Doctors**: Can create policies and forms for their patients, view their patients' insurance data
- **Patients**: Can only view their own insurance policies and forms

## AI Approval Process

The system includes an AI-based approval process for insurance claims:

1. An admin submits the claim for AI analysis
2. The AI system evaluates the claim based on various factors
3. The AI returns an approval decision with a confidence score and detailed analysis
4. If approved by AI, the claim can be automatically approved in the system
5. The AI approval status is tracked in the system for audit purposes

## Pre-Authorization and Cashless Claims Workflow

### Pre-Authorization Process

1. **Form Creation**: Doctor or admin creates an insurance form with `is_cashless_claim` set to true
2. **Pre-Auth Submission**: The form is submitted with status changing to `pre_auth_pending`
3. **Review**: Admin reviews the pre-authorization request
4. **Pre-Auth Decision**: 
   - If approved, status changes to `pre_auth_approved`, and `pre_authorization_reference` and `pre_authorized_amount` are recorded
   - If rejected, status changes to `pre_auth_rejected` with `rejection_reason`

### Enhancement Request Process

1. **Treatment Progress**: During treatment, if additional funds are needed beyond pre-authorized amount
2. **Enhancement Request**: Doctor or admin submits enhancement request with `enhancement_amount` and `enhancement_reason`
3. **Status Update**: Form status changes to `enhancement_requested`
4. **Enhancement Review**: Admin reviews and makes decision on enhancement request
   - Can approve with increase in `pre_authorized_amount`
   - Can reject with reason

### Claim Finalization Process

1. **Treatment Completion**: When treatment is complete, doctor or admin finalizes the claim
2. **Final Amount**: Final claim amount is updated if different from pre-authorized amount
3. **Status Update**: Form status changes to `payment_pending`
4. **Payment Processing**: Admin marks payment as completed once insurance company processes payment
5. **Completion**: Status changes to `payment_completed`

### Status Flow for Cashless Claims

```
draft → pre_auth_pending → pre_auth_approved → enhancement_requested (optional) → payment_pending → payment_completed
      ↘                  → pre_auth_rejected
```

### API Endpoints for Cashless Workflow

- Submit for pre-authorization: `POST /api/insurance/forms/{id}/submit/`
- Approve pre-authorization: `POST /api/insurance/forms/{id}/approve/`
- Reject pre-authorization: `POST /api/insurance/forms/{id}/reject/`
- Request enhancement: `POST /api/insurance/forms/{id}/request_enhancement/`
- Finalize claim: `POST /api/insurance/forms/{id}/finalize_claim/`
- Mark payment completed: `POST /api/insurance/forms/{id}/mark_payment_completed/`

## EHR Integration

The Insurance Module is fully integrated with the EHR system, allowing for automated form creation and data synchronization between patient visits and insurance claims.

### Auto-Creation from EHR Data

Insurance forms can be automatically generated from existing patient visit data, minimizing manual data entry and reducing errors. The system can extract relevant information from:

- Patient visits and medical records
- Diagnoses and clinical notes
- Lab results and investigation reports
- Prescriptions and medications
- Vital signs and medical findings
- Visit charges and billing information

### Methods for EHR Integration

There are three main ways to integrate insurance forms with EHR data:

1. **Auto-Create from Visit API Endpoint**
   - `POST /api/insurance/forms/auto_create_from_visit/`
   - Automatically creates a new insurance form using existing visit data
   - Pulls in diagnoses, lab results, vital signs, and other clinical data

2. **Auto-Populate During Form Creation**
   - When creating a form via the regular endpoint, include `auto_populate: true`
   - Extracts relevant data from the visit while still allowing manual input

3. **Update Form with Latest Visit Data**
   - `POST /api/insurance/forms/{id}/update_from_visit_data/`
   - Updates an existing form with the latest data from the linked visit
   - Useful when visit details are updated after the form was created

### Data Sources for Auto-Population

The system pulls data from various EHR sources to populate insurance forms:

| Insurance Form Field | EHR Data Source |
|---------------------|-----------------|
| Diagnosis | Diagnosis.diagnosis or PatientVisit.diagnosis |
| Treatment Description | PatientVisit.treatment_notes |
| Clinical Findings | Most recent VitalSigns |
| Investigation Details | LabResult entries |
| Treatment Description | Prescription medications |
| Financial Details | VisitCharge entries |
| Patient Medical History | UserProfile.chronic_conditions |
| Treating Doctor | PatientVisit.attending_doctor |

### Example: Auto-Creating a Form from Visit Data

```json
// POST /api/insurance/forms/auto_create_from_visit/
{
  "visit_id": 123,
  "policy_id": 456,
  "is_cashless": true
}
```

### Example: Auto-Populating During Form Creation

```json
// POST /api/insurance/forms/
{
  "visit": 123,
  "policy": 456,
  "is_cashless_claim": true,
  "auto_populate": true
}
```
