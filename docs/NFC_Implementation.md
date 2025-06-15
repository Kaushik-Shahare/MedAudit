# NFC-Enabled EHR System Documentation

## Overview

This document outlines the implementation of the NFC-enabled Electronic Health Record (EHR) system for MedAudit. The system allows patients to use NFC cards for seamless check-in at healthcare facilities, grants temporary access to their medical records, and provides emergency access capabilities.

## Key Features

1. **NFC Card Management**
   - Each patient can have a unique NFC card linked to their account
   - Cards can be activated/deactivated by administrators
   - QR codes can serve as NFC alternatives for devices without NFC hardware

2. **Temporary Session Management**
   - When a patient taps their NFC card, a 4-hour access session is created
   - Healthcare providers can access patient records during this session
   - Sessions can be manually invalidated if needed

3. **Emergency Access**
   - Patients can mark specific documents as emergency-accessible
   - Emergency QR codes provide access to vital information
   - Emergency access is time-limited (24 hours) and tracked

## Technical Implementation

### Models

1. **NFCCard**
   - Links a patient to a unique NFC identifier
   - Tracks card status and usage

2. **NFCSession**
   - Created when a patient taps their NFC card
   - Provides 4-hour access to patient records
   - Contains authentication tokens

3. **EmergencyAccess**
   - Provides limited access to vital medical information
   - Uses unique tokens for secure access
   - Tracks access events

### API Endpoints

#### NFC Management
- `POST /api/ehr/nfc-cards/{id}/tap/` - Simulate NFC card tap
- `GET /api/ehr/nfc/verify-session/?token={token}` - Verify session validity
- `GET /api/ehr/nfc/generate-qr/` - Generate QR code for NFC emulation

#### Emergency Access
- `GET /api/ehr/emergency/generate-qr/` - Generate emergency access QR code
- `GET /api/ehr/emergency-access/{token}/` - Access emergency medical information
- `GET /api/ehr/patient/emergency-docs/` - Manage emergency-accessible documents

### Security Considerations

1. **NFC Authentication**
   - Sessions are time-limited (4 hours)
   - Each session has a unique token
   - Sessions can be invalidated by patients or staff

2. **Emergency Access**
   - Limited to designated emergency-accessible documents only
   - Time-limited (24 hours)
   - All access events are logged and tracked

## Frontend Implementation

The frontend components include:

1. **NFCCardReader Component**
   - Simulates NFC card taps
   - Generates QR codes for NFC emulation
   - Shows session status and countdown

2. **EmergencyAccessView Component**
   - Displays emergency medical information
   - Shows time-remaining for emergency access
   - Renders emergency-accessible documents

## User Flows

### Patient Check-In via NFC

1. Patient arrives at healthcare facility
2. Patient taps NFC card (or scans QR code) at check-in
3. System creates 4-hour access session
4. Healthcare providers can access patient's EHR during session

### Emergency Access

1. First responder or medical professional scans emergency QR code
2. System validates the emergency token
3. System displays vital medical information and emergency-accessible documents
4. Access is limited to emergency information only and expires after 24 hours

## Integration Guide

### Adding NFC to a Patient Account

1. Admin creates an NFC card for a patient in the admin panel
2. Patient receives the physical NFC card
3. Patient configures emergency-accessible documents

### Implementing NFC Reader

For hardware implementation:
- Use standard NFC readers compatible with ISO/IEC 14443
- Configure to read UUID from NFC cards
- Send UUID to API for validation

For QR code alternative:
- Generate QR code containing session token
- Scan QR code with standard barcode scanner
- Validate token with API

## Testing & Deployment

To test the NFC functionality:
1. Create test patient accounts
2. Add NFC cards to patients
3. Test tapping and session creation
4. Verify document access permissions
5. Test emergency access scenarios

For production deployment:
1. Ensure secure token handling
2. Implement proper SSL/TLS
3. Set up monitoring for session and access events
4. Configure token expiry based on organizational policy
