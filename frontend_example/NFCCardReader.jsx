import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, Button, Alert, Spinner, Row, Col } from 'react-bootstrap';

// NFCCardReader component - handles NFC card taps and QR code generation
const NFCCardReader = ({ token, apiUrl }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nfcSession, setNfcSession] = useState(null);
  const [qrCode, setQrCode] = useState(null);
  const [remainingTime, setRemainingTime] = useState(null);
  const [countdown, setCountdown] = useState(null);

  // Handle NFC reading
  const handleNfcTap = async () => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Simulate NFC tap by calling the API endpoint
      const { data } = await axios.post(
        `${apiUrl}/api/ehr/nfc-cards/1/tap/`, 
        {}, 
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setNfcSession(data);
      
      // Calculate session expiry time
      const expiryTime = new Date(data.expires_at);
      const timeRemaining = Math.floor((expiryTime - new Date()) / 1000);
      setRemainingTime(timeRemaining);
      
      // Start countdown
      startCountdown(timeRemaining);
      
    } catch (err) {
      console.error("NFC tap error:", err);
      setError(err.response?.data?.detail || "Error during NFC tap simulation");
    } finally {
      setLoading(false);
    }
  };
  
  // Generate QR code for NFC emulation
  const generateQrCode = async () => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const { data } = await axios.get(
        `${apiUrl}/api/ehr/nfc/generate-qr/`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setQrCode(data.qr_code);
      
    } catch (err) {
      console.error("QR code generation error:", err);
      setError(err.response?.data?.detail || "Error generating QR code");
    } finally {
      setLoading(false);
    }
  };
  
  // Generate emergency QR code
  const generateEmergencyQr = async () => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const { data } = await axios.get(
        `${apiUrl}/api/ehr/emergency/generate-qr/`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setQrCode(data.qr_code);
      
    } catch (err) {
      console.error("Emergency QR code generation error:", err);
      setError(err.response?.data?.detail || "Error generating emergency QR code");
    } finally {
      setLoading(false);
    }
  };
  
  // Countdown timer for session validity
  const startCountdown = (seconds) => {
    if (countdown) clearInterval(countdown);
    
    const timer = setInterval(() => {
      setRemainingTime(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          setNfcSession(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    setCountdown(timer);
  };
  
  // Format remaining time as HH:MM:SS
  const formatTime = (seconds) => {
    if (!seconds) return '--:--:--';
    
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return [hrs, mins, secs]
      .map(v => v < 10 ? `0${v}` : v)
      .join(':');
  };
  
  // Clear session on unmount
  useEffect(() => {
    return () => {
      if (countdown) clearInterval(countdown);
    };
  }, [countdown]);

  return (
    <Card className="shadow-sm mb-4">
      <Card.Header as="h5">NFC Patient Identification</Card.Header>
      <Card.Body>
        {error && (
          <Alert variant="danger" onClose={() => setError(null)} dismissible>
            {error}
          </Alert>
        )}
        
        {nfcSession ? (
          <div className="text-center mb-3">
            <h6>Active Session</h6>
            <p className="mb-1">Patient ID: {nfcSession.patient}</p>
            <p className="mb-1">Session started: {new Date(nfcSession.started_at).toLocaleString()}</p>
            <p className="mb-1">Expires in: {formatTime(remainingTime)}</p>
            <Alert variant="success">
              Your medical records are available for the next 4 hours
            </Alert>
          </div>
        ) : (
          <p>No active NFC session. Tap your NFC card or generate a QR code to check in.</p>
        )}
        
        <Row className="mt-3">
          <Col>
            <Button 
              variant="primary" 
              className="w-100"
              onClick={handleNfcTap}
              disabled={loading}
            >
              {loading ? <Spinner size="sm" animation="border" /> : "Simulate NFC Tap"}
            </Button>
          </Col>
          
          <Col>
            <Button
              variant="secondary"
              className="w-100"
              onClick={generateQrCode}
              disabled={loading}
            >
              Generate QR Code
            </Button>
          </Col>
          
          <Col>
            <Button
              variant="danger"
              className="w-100"
              onClick={generateEmergencyQr}
              disabled={loading}
            >
              Emergency Access QR
            </Button>
          </Col>
        </Row>
        
        {qrCode && (
          <div className="text-center mt-4">
            <h6>QR Code for Check-in</h6>
            <img 
              src={qrCode} 
              alt="NFC QR Code" 
              style={{ maxWidth: "200px" }} 
              className="border"
            />
            <p className="mt-2 small text-muted">
              Scan this QR code to check in or provide emergency access
            </p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default NFCCardReader;
