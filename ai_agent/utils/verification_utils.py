import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def extract_document_content(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract content from medical documents
    """
    extracted_documents = []
    for doc in documents:
        try:
            extracted_documents.append({
                "document_type": doc.get("document_type", "Unknown"),
                "content": doc.get("content", "No content available"),
                "metadata": {
                    "uploaded_at": doc.get("uploaded_at", "Unknown"),
                    "description": doc.get("description", "")
                }
            })
        except Exception as e:
            logger.exception(f"Error extracting document content: {str(e)}")
    
    return extracted_documents

def calculate_coverage_amount(claim_amount: float, coverage_percentage: float, 
                             max_coverage_amount: Optional[float] = None) -> float:
    """
    Calculate insurance coverage amount based on policy details
    """
    coverage = claim_amount * (coverage_percentage / 100)
    
    if max_coverage_amount is not None:
        coverage = min(coverage, max_coverage_amount)
    
    return coverage

def is_policy_active(valid_from: str, valid_till: str, current_date: str) -> bool:
    """
    Check if an insurance policy is active on a given date
    """
    from datetime import datetime
    
    try:
        valid_from_date = datetime.fromisoformat(valid_from)
        valid_till_date = datetime.fromisoformat(valid_till)
        current_date = datetime.fromisoformat(current_date)
        
        return valid_from_date <= current_date <= valid_till_date
    except Exception as e:
        logger.exception(f"Error checking policy active status: {str(e)}")
        return False

def calculate_confidence_weighted_average(verifications: Dict[str, Any], 
                                         weights: Dict[str, float] = None) -> float:
    """
    Calculate weighted average of confidence scores from different verifications
    """
    if weights is None:
        weights = {
            "eligibility": 0.2,
            "diagnostic": 0.2,
            "treatment": 0.2,
            "billing": 0.2,
            "fraud_detection": 0.2
        }
    
    total_weight = sum(weights.values())
    weighted_sum = 0
    
    for verification_type, weight in weights.items():
        verification = verifications.get(verification_type, {})
        confidence = verification.get("confidence_score", 0.0)
        weighted_sum += confidence * weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0
