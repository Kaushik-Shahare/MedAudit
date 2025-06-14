from django.contrib import admin
from .models import PatientProfile, DoctorProfile, Document, AccessRequest

# Register your models here.
admin.site.register(PatientProfile)
admin.site.register(DoctorProfile)
admin.site.register(Document)
admin.site.register(AccessRequest)
