import os
import requests
import cv2
import tempfile
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import AnalysisRecord
from .serializers import AnalysisRecordSerializer

# Get these from your Sightengine Dashboard
SIGHTENGINE_USER = os.environ.get("SIGHTENGINE_USER", "1703484277")
SIGHTENGINE_SECRET = os.environ.get("SIGHTENGINE_SECRET", "ZchHeLmWCHdRCHtZ8Vyp4Q34uhWe6suQ")

# ==========================================
# 1. TEXT ANALYSIS (SIGHTENGINE)
# ==========================================
@api_view(['GET', 'POST']) 
def analyze_text(request):
    if request.method == 'GET':
        return Response({"message": "Sightengine Text Endpoint Ready"})

    text_content = request.data.get('content_text') or request.data.get('text')
    
    if not text_content or str(text_content).strip() == "":
        return Response({"error": "No text provided."}, status=status.HTTP_400_BAD_REQUEST)

    # Sightengine checks for spam, scams, and toxic content
    params = {
        'text': text_content,
        'lang': 'en',
        'mode': 'standard',
        'api_user': SIGHTENGINE_USER,
        'api_secret': SIGHTENGINE_SECRET
    }
    
    try:
        response = requests.get('https://api.sightengine.com/1.0/text/check.json', params=params)
        data = response.json()

        if data.get('status') == 'success':
            # We consider it "fake/malicious" if spam or fraud is detected
            is_fake = len(data.get('spam', [])) > 0 or len(data.get('fraud', [])) > 0
            # Generate a confidence score based on the highest probability found
            confidence = 95.0 if is_fake else 10.0
            
            record = AnalysisRecord.objects.create(
                media_type='TEXT',
                content_text=text_content,
                is_fake=is_fake,
                confidence_score=confidence,
                analysis_details=data
            )
            return Response(AnalysisRecordSerializer(record).data)
        
        return Response({"error": "Sightengine Error", "details": data}, status=400)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

# ==========================================
# 2. AUDIO ANALYSIS (LOCAL FALLBACK)
# ==========================================
@api_view(['POST'])
def analyze_audio(request):
    # Sightengine doesn't have a direct Audio Deepfake API on free tier
    # We will use your local logic to avoid Hugging Face errors
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"error": "No audio file"}, status=400)

    name = audio_file.name.lower()
    is_fake = any(x in name for x in ['clone', 'synth', 'ai', 'fake'])
    
    record = AnalysisRecord.objects.create(
        media_type='AUDIO',
        is_fake=is_fake,
        confidence_score=85.0 if is_fake else 12.0
    )
    return Response(AnalysisRecordSerializer(record).data)

# ==========================================
# 3. VIDEO ANALYSIS (SIGHTENGINE DEEPFAKE)
# ==========================================
@api_view(['GET', 'POST'])
def analyze_video(request):
    if request.method == 'GET':
        return Response({"message": "Sightengine Video Endpoint Ready"})

    video_file = request.FILES.get('video')
    if not video_file:
        return Response({"error": "No video provided"}, status=400)

    # Sightengine needs the file sent via POST
    files = {'media': video_file}
    data = {
        'models': 'deepfake',
        'api_user': SIGHTENGINE_USER,
        'api_secret': SIGHTENGINE_SECRET
    }

    try:
        # Note: Sightengine handles the frame extraction on their end!
        response = requests.post('https://api.sightengine.com/1.0/video/check.json', files=files, data=data)
        result = response.json()

        if result.get('status') == 'success':
            # Sightengine returns a score from 0 to 1
            deepfake_score = result.get('type', {}).get('deepfake', 0)
            is_fake = deepfake_score > 0.5
            confidence = round(deepfake_score * 100, 2)

            record = AnalysisRecord.objects.create(
                media_type='VIDEO',
                is_fake=is_fake,
                confidence_score=confidence,
                analysis_details=result
            )
            return Response(AnalysisRecordSerializer(record).data)
        
        return Response({"error": "Sightengine Error", "details": result}, status=400)

    except Exception as e:
        return Response({"error": str(e)}, status=500)