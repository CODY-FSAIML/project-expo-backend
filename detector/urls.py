# detector/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/analyze-text/', views.analyze_text, name='analyze_text'),
    path('api/analyze-audio/', views.analyze_audio, name='analyze_audio'),
    path('api/analyze-video/', views.analyze_video, name='analyze_video'),
]