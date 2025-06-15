# Utility functions for NFC and QR code functionality
import qrcode
from io import BytesIO
import base64
from django.conf import settings
from datetime import timedelta
from .models import NFCSession, EmergencyAccess
from django.utils import timezone

def generate_nfc_qr_code(nfc_card):
    """
    Generate a QR code for NFC emulation.
    
    This creates a QR code containing the NFC card information
    that can be used by devices without NFC hardware.
    """
    # Create a session for 4-hour access
    session = NFCSession.objects.create(
        patient=nfc_card.patient,
        expires_at=timezone.now() + timedelta(hours=4)
    )
    
    # Generate the QR code with the session token
    session_data = {
        'session_token': session.session_token,
        'patient_id': nfc_card.patient.id,
        'nfc_card_id': str(nfc_card.card_id),
        'expires_at': session.expires_at.isoformat()
    }
    
    # Convert session data to QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    import json
    qr.add_data(json.dumps(session_data))
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    # Return base64 encoded image
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{qr_code_base64}"

def generate_emergency_qr_code(patient):
    """
    Generate an emergency QR code for accessing vital patient information.
    
    This creates a QR code containing an emergency access token that
    can be scanned to view vital patient information without authentication.
    """
    # Create an emergency access token valid for 24 hours
    emergency_access = EmergencyAccess.objects.create(
        patient=patient,
        expires_at=timezone.now() + timedelta(hours=24)
    )
    
    # Generate QR code with emergency access URL
    emergency_url = f"{settings.SITE_URL}/emergency/{emergency_access.access_token}/"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(emergency_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    # Return base64 encoded image
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{qr_code_base64}"
