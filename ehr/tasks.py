from celery import shared_task
import logging
from django.utils import timezone
import json
import traceback
import pdfplumber
import tempfile
import os
import requests
from .models import Document

@shared_task
def process_pdfdocument_parsing(pdf_document_id):
    """
    Process the PDF document parsing task.
    This function should contain the logic to parse the PDF document from Cloudinary.
    
    1. Download the file from Cloudinary to a temporary location
    2. Process it with pdfplumber
    3. Clean up the temporary file
    """
    logger = logging.getLogger(__name__)
    temp_file = None
    
    try:
        # Get the PDF document
        pdf_document = Document.objects.get(id=pdf_document_id)
        
        # Get the URL of the file from Cloudinary
        file_url = pdf_document.file.url
        logger.info(f"Downloading PDF from Cloudinary URL: {file_url}")
        
        # Create a temporary file to store the downloaded PDF
        temp_file_handle, temp_file_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_file_handle)  # Close the file handle
        
        # Download the file from Cloudinary
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded PDF to temporary file: {temp_file_path}")
            
            # Open the downloaded PDF file using pdfplumber
            with pdfplumber.open(temp_file_path) as pdf:
                # Extract text from each page
                text = ""
                for page in pdf.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:  # Check if text extraction was successful
                        text += extracted_text + "\n"
                    else:
                        logger.warning(f"Could not extract text from page in document ID {pdf_document_id}")
                
                # Save the extracted text back to the document's content field
                pdf_document.content = text
                pdf_document.save(update_fields=['content'])  # Only update the content field to avoid triggering the signal again
                
                logger.info(f"Successfully parsed and saved content for document ID: {pdf_document_id}")
        else:
            logger.error(f"Failed to download PDF from Cloudinary. Status code: {response.status_code}")
            return f"Failed to download PDF document {pdf_document_id} from Cloudinary"
            
        return f"Successfully parsed PDF document {pdf_document_id}"
    except Document.DoesNotExist:
        logger.error(f"Document with ID {pdf_document_id} does not exist.")
        return f"Document with ID {pdf_document_id} does not exist."
    except Exception as e:
        logger.error(f"Error processing PDF document {pdf_document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error processing PDF document {pdf_document_id}: {str(e)}"
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")
