# detector/admin.py
from django.contrib import admin
from .models import AnalysisRecord

# Register your model here so it appears in the admin dashboard
admin.site.register(AnalysisRecord)