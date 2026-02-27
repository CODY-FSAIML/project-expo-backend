# detector/serializers.py
from rest_framework import serializers
from .models import AnalysisRecord

class AnalysisRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRecord
        fields = '__all__' # This tells Django to convert ALL columns in the database to JSON