from django.db import models

# Create your models here.

class InsuranceDocument(models.Model):
    """
    Model for digital insurance documents.
    """
    document_id = models.AutoField(primary_key=True)
    patient_id = models.CharField(max_length=100, unique=True)
    document_type = models.CharField(max_length=50)  # e.g., 'policy', 'claim'
    document_content = models.TextField()  # Store the content of the document
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for {self.patient_id}"
