# MedAudit - Secure Medical Records Management System

## Project Overview

MedAudit is a comprehensive medical records management system designed to securely store, access, and share electronic health records (EHR) between patients and healthcare providers. The platform emphasizes security, accessibility, and emergency access through innovative technologies like NFC card authentication and QR code generation.

## Key Features

- **Secure EHR Management**: Store and manage patient medical documents with robust access controls
- **Role-Based Access**: Distinct permissions for patients, doctors, and administrators
- **NFC Authentication**: Tap-to-access functionality using NFC cards with 4-hour session validity
- **Emergency Access**: Temporary access to critical medical documents in emergency situations
- **QR Code Integration**: NFC emulation through QR codes for devices without NFC capabilities
- **Cloudinary Integration**: Secure cloud storage for medical documents

## Backend Architecture

### Technology Stack
- **Framework**: Django (Python)
- **API**: Django REST Framework
- **Database**: SQLite3 (Development), PostgreSQL (Production ready)
- **File Storage**: Cloudinary
- **Authentication**: JWT (JSON Web Tokens)

### Core Models

#### User Management
- `User`: Extended Django user model with custom user types (Patient, Doctor, Admin)
- `UserProfile`: Profile information specific to user roles (Patient info, Doctor specialization)
- `UserType`: Role definitions with associated permissions
- `Permission`: Granular permission definitions

#### Electronic Health Records
- `Document`: Medical document storage with patient association and approval workflow
- `AccessRequest`: Doctor's request for accessing a patient's medical records

#### NFC & Emergency Access
- `NFCCard`: Links patients to their NFC cards for authentication
- `NFCSession`: Manages temporary access sessions (4-hour validity)
- `EmergencyAccess`: Handles emergency access tokens (24-hour validity)

### API Endpoints

#### Document Management
```
GET/POST /api/documents/ - List and create documents
GET/PUT/DELETE /api/documents/{id}/ - Retrieve, update or delete specific document
POST /api/documents/{id}/toggle_emergency_access/ - Toggle emergency accessibility
POST /api/documents/{id}/approve/ - Admin approval for documents
```

#### Access Control
```
GET/POST /api/access-requests/ - List and create access requests
POST /api/access-requests/{id}/approve/ - Approve doctor's access request
```

#### NFC Functionality
```
GET/POST /api/nfc-cards/ - Manage NFC cards
POST /api/nfc-tap/{card_id}/ - Simulate NFC card tap
GET /api/nfc-session/{token}/ - Validate NFC session
```

#### Emergency Access
```
POST /api/emergency-access/create/ - Create emergency access token
GET /public/emergency/{token}/ - Access emergency documents with token
```

#### QR Code Generation
```
GET /api/generate-nfc-qr/{card_id}/ - Generate QR code for NFC emulation
GET /api/generate-emergency-qr/{token}/ - Generate QR code for emergency access
```

## Security Features

1. **JWT Authentication**: Secure API access using token-based authentication
2. **Session Expiry**: Automatic expiration of NFC sessions after 4 hours
3. **Emergency Token Expiry**: 24-hour validity for emergency access tokens
4. **Document-Level Permissions**: Granular control over document accessibility
5. **Audit Logging**: Comprehensive logging of all access attempts and changes


## Getting Started

### Prerequisites
- Python 3.8+
- Django 4.2+
- Cloudinary account for document storage

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/MedAudit.git
cd MedAudit
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Apply migrations
```bash
python manage.py migrate
```

5. Create superuser
```bash
python manage.py createsuperuser
```

6. Load initial user types
```bash
python manage.py load_usertypes
```

7. Run the development server
```bash
python manage.py runserver
```

