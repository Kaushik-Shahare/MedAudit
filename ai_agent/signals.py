from django.db.models.signals import post_save
from django.dispatch import receiver
from insurance.models import InsuranceForm
from .tasks.verification import trigger_insurance_verification

@receiver(post_save, sender=InsuranceForm)
def initiate_ai_verification(sender, instance, created, **kwargs):
    """
    Signal handler to automatically trigger AI verification when a new insurance form is created
    or when an insurance form status changes to 'submitted'
    """
    if instance.status == 'submitted':
        # Trigger the background verification task
        trigger_insurance_verification.delay(instance.id)
