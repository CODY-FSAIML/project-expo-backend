# detector/models.py
from django.db import models

class AnalysisRecord(models.Model):
    # Defining the types of media we accept
    MEDIA_CHOICES = (
        ('TEXT', 'Text/SMS'),
        ('AUDIO', 'Audio/Voice'),
        ('VIDEO', 'Video'),
    )

    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES)
    
    # We leave these blank=True because a text analysis won't have a file, 
    # and a video analysis won't have text!
    content_text = models.TextField(blank=True, null=True) 
    media_file = models.FileField(upload_to='uploads/', blank=True, null=True) 
    
    # AI Analysis Results
    is_fake = models.BooleanField(default=False)
    confidence_score = models.FloatField(null=True, blank=True)
    
    # JSONField is great for storing extra data from external APIs
    analysis_details = models.JSONField(blank=True, null=True) 
    
    # Automatically saves the date and time this record was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This makes it readable in the Django Admin panel
        status = 'Fake' if self.is_fake else 'Real'
        return f"{self.media_type} Analysis - {status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"