import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, Alert, Spinner, ListGroup, Badge } from 'react-bootstrap';

// EmergencyAccessView - renders emergency medical data for a patient
const EmergencyAccessView = ({ token, apiUrl }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emergencyData, setEmergencyData] = useState(null);
  const [remainingTime, setRemainingTime] = useState(null);
  const [countdown, setCountdown] = useState(null);

  useEffect(() => {
    fetchEmergencyData();
    
    return () => {
      if (countdown) clearInterval(countdown);
    };
  }, [token]);

  const fetchEmergencyData = async () => {
    if (!token) {
      setError("No emergency access token provided");
      setLoading(false);
      return;
    }
    
    try {
      const { data } = await axios.get(
        `${apiUrl}/api/ehr/emergency-access/${token}/`
      );
      
      setEmergencyData(data);
      
      // Calculate expiry time
      const expiryTime = new Date(data.access_expires);
      const timeRemaining = Math.floor((expiryTime - new Date()) / 1000);
      setRemainingTime(timeRemaining);
      
      // Start countdown
      startCountdown(timeRemaining);
      
    } catch (err) {
      console.error("Emergency access error:", err);
      setError(err.response?.data?.detail || "Error accessing emergency information");
    } finally {
      setLoading(false);
    }
  };
  
  // Countdown timer for access validity
  const startCountdown = (seconds) => {
    if (countdown) clearInterval(countdown);
    
    const timer = setInterval(() => {
      setRemainingTime(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          setError("Emergency access has expired");
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
  
  if (loading) {
    return (
      <div className="text-center p-5">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
        <p className="mt-2">Loading emergency medical information...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <Alert variant="danger">
        <Alert.Heading>Error</Alert.Heading>
        <p>{error}</p>
      </Alert>
    );
  }

  return (
    <div>
      <Alert variant="danger">
        <Alert.Heading>EMERGENCY MEDICAL INFORMATION</Alert.Heading>
        <p>
          This emergency access is valid for: {formatTime(remainingTime)}
        </p>
      </Alert>
      
      <Card className="mb-4">
        <Card.Header as="h5">Patient Information</Card.Header>
        <Card.Body>
          <p><strong>Name:</strong> {emergencyData.patient.name || 'Not provided'}</p>
          {emergencyData.patient.date_of_birth && (
            <p><strong>Date of Birth:</strong> {new Date(emergencyData.patient.date_of_birth).toLocaleDateString()}</p>
          )}
          {emergencyData.patient.phone_number && (
            <p><strong>Contact:</strong> {emergencyData.patient.phone_number}</p>
          )}
        </Card.Body>
      </Card>
      
      <Card className="mb-4">
        <Card.Header as="h5">Medical Documents</Card.Header>
        <ListGroup variant="flush">
          {emergencyData.documents.length === 0 ? (
            <ListGroup.Item>No emergency-accessible documents available</ListGroup.Item>
          ) : (
            emergencyData.documents.map(doc => (
              <ListGroup.Item key={doc.id} className="d-flex justify-content-between align-items-center">
                <div>
                  <h6>{doc.description || 'Document'}</h6>
                  <small className="text-muted">
                    {new Date(doc.uploaded_at).toLocaleString()}
                  </small>
                </div>
                <div>
                  <Badge bg="info" className="me-2">{doc.document_type || 'Document'}</Badge>
                  <a href={doc.file} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-primary">View</a>
                </div>
              </ListGroup.Item>
            ))
          )}
        </ListGroup>
      </Card>
      
      <Alert variant="warning">
        <strong>Note for Medical Professionals:</strong> This is a limited view of the patient's medical record.
        For full access, please login to the MedAudit system or contact the patient's primary healthcare provider.
      </Alert>
    </div>
  );
};

export default EmergencyAccessView;
