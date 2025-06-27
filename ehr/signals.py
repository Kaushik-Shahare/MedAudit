import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Document
from .tasks import process_pdfdocument_parsing
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Document)
def parse_pdf_document(sender, instance, created, **kwargs):
    """
    Signal handler to process document parsing after a document is saved.
    Only processes PDF files and only when they are first created.
    Handles documents stored in Cloudinary.
    """
    if created:
        # Get the file extension (lowercase)
        _, file_extension = os.path.splitext(instance.file.name)
        file_extension = file_extension.lower()
        
        # Check if the document is a PDF
        if file_extension == '.pdf':
            try:
                logger.info(f"Dispatching PDF parsing task for document ID: {instance.id} with filename: {instance.file.name}")
                # Dispatch the Celery task asynchronously
                process_pdfdocument_parsing.delay(instance.id)
                logger.info(f"Successfully dispatched PDF parsing task for document ID: {instance.id}")
            except Exception as e:
                logger.error(f"Error dispatching PDF parsing task for document ID {instance.id}: {str(e)}")
        else:
            logger.info(f"Skipping document parsing for non-PDF file: {instance.file.name} (ID: {instance.id})")
