from django.contrib import admin
from .models import Document, AccessRequest

# Register your models here.
admin.site.register(Document)
admin.site.register(AccessRequest)
