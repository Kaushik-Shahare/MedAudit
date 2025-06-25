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

Represents an insurance claim form linked to a patient visit.

- **visit**: The patient visit this insurance form is for
- **policy**: The insurance policy being claimed
- **created_by**: User who created this form (doctor or admin)
- **diagnosis**: Diagnosis description
- **treatment_description**: Description of treatment provided
- **claim_amount**: Amount being claimed
- **approved_amount**: Approved amount (if claim is approved)
- **status**: Current status of the form (draft, submitted, approved, etc.)
- **reference_number**: Unique reference number for this claim
- **is_ai_approved**: Whether this claim was approved by AI
- **ai_confidence_score**: Confidence score from AI analysis
- **ai_analysis**: Detailed analysis data from AI
- **is_cashless_claim**: Whether this is a cashless claim
- **pre_authorization_reference**: Pre-authorization reference for cashless claims

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
- `POST /api/insurance/forms/`: Create a new insurance form
- `GET /api/insurance/forms/{id}/`: Get details of a specific form
- `PUT/PATCH /api/insurance/forms/{id}/`: Update an insurance form
- `DELETE /api/insurance/forms/{id}/`: Delete an insurance form
- `POST /api/insurance/forms/{id}/submit/`: Submit an insurance form for processing
- `POST /api/insurance/forms/{id}/approve/`: Approve an insurance form (admin only)
- `POST /api/insurance/forms/{id}/reject/`: Reject an insurance form (admin only)
- `POST /api/insurance/forms/{id}/ai_approval/`: Process AI approval for a form (admin only)
- `GET /api/insurance/forms/visit_forms/?visit_id=X`: Get forms for a specific visit
- `GET /api/insurance/forms/cashless_claims/`: Get only cashless insurance claims

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

## Cashless Claims Process

For cashless insurance claims:

1. The doctor or admin creates a form with `is_cashless_claim` set to true
2. If pre-authorization is required, the pre-authorization details are provided
3. The system tracks pre-authorized amounts separately from final approved amounts
4. The insurance provider can then process the claim without the patient paying upfront
