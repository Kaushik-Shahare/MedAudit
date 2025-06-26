# AI Claim Verification System

## Overview

The AI Claim Verification system is a sophisticated multi-agent system designed to automate and enhance the insurance claim verification process. It integrates with the MedAudit platform to provide thorough, consistent, and explainable verification of medical insurance claims.

## System Architecture

The verification system employs a multi-agent architecture with specialized agents focused on different aspects of claim verification:

1. **Eligibility Agent**: Verifies patient eligibility for insurance coverage
2. **Diagnostic Agent**: Validates diagnosis codes and medical necessity
3. **Treatment Agent**: Evaluates if treatments are appropriate for the diagnosis
4. **Billing Agent**: Checks billing amounts and codes for accuracy
5. **Fraud Detection Agent**: Identifies potential fraud indicators
6. **[Reflexion Agent](ReflexionAgent.md)**: Meta-agent that reviews and improves verification results

## Workflow

The verification process follows a sequential workflow:

1. Claim data is collected from the insurance form, patient records, and visit details
2. Each specialized agent performs its verification task
3. The Reflexion Agent analyzes and improves the combined results
4. A final verification result with confidence score is produced
5. Results are saved to the database and linked to the insurance claim

## Key Features

- **Multi-aspect Verification**: Comprehensive analysis across multiple verification dimensions
- **Confidence Scoring**: Each verification includes confidence scores for decision-making
- **Detailed Reasoning**: Clear explanations for verification decisions
- **[Reflexive Improvement](ReflexionAgent.md)**: Multiple iterations of reflection improve accuracy
- **Asynchronous Processing**: Verification runs as background tasks via Celery
- **Fallback Mechanisms**: System remains operational even when external services fail

## API Endpoints

### Trigger Verification

**POST** `/api/ai/verification/{insurance_form_id}/`

Triggers the AI verification process for an insurance claim.

### Check Verification Status

**GET** `/api/ai/verification/{insurance_form_id}/`

Returns the current status and results of the verification process.

## Integration with Insurance Module

The AI verification system integrates with the MedAudit insurance module through:

1. Database connections to insurance forms and policies
2. Celery tasks triggered by form submissions or manual requests
3. API endpoints for triggering and checking verification status
4. Automatic updates to insurance form records with verification results

## Reflexion Agent

The [Reflexion Agent](ReflexionAgent.md) is a critical component that improves verification quality through iterative self-reflection. See the [Reflexion Agent Documentation](ReflexionAgent.md) for a detailed explanation of this component.

## Configuration

The AI verification system can be configured through environment variables:

- `GOOGLE_API_KEY`: API key for Google's Generative AI models
- `GOOGLE_MODEL_NAME`: Model name (default: "gemini-2.0-flash")
- `AI_VERIFICATION_CONFIDENCE_THRESHOLD`: Minimum confidence for automatic approval

## Error Handling

The system implements comprehensive error handling:

1. Exception catching and logging at all workflow stages
2. Fallback to mock responses when external services are unavailable
3. Detailed error messages saved with failed verifications
4. Automatic retries for transient errors

## Performance Considerations

- Verification runs as background tasks to avoid blocking user interactions
- Resource-intensive operations are optimized for speed and reliability
- Mock modes allow for testing and development without external API dependencies
