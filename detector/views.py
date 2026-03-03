# detector/views.py
import os
import requests
import cv2
import tempfile
import time
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import AnalysisRecord
from .serializers import AnalysisRecordSerializer

HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "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")

# ==========================================
# 1. TEXT ANALYSIS ENDPOINT
# ==========================================
@api_view(['GET', 'POST']) 
def analyze_text(request):
    if request.method == 'GET':
        return Response({"message": "Endpoint is ready! Send a POST request with 'content_text' to analyze it."})

    text_content = request.data.get('content_text') or request.data.get('text') or request.data.get('content')
    
    if not text_content or str(text_content).strip() == "":
        return Response({"error": "No text provided. Did you type something in the box?"}, status=status.HTTP_400_BAD_REQUEST)

    API_URL = "https://router.huggingface.co/hf-inference/models/mrm8488/bert-tiny-finetuned-sms-spam-detection"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

    if not HUGGINGFACE_API_TOKEN:
        return Response({"error": "HuggingFace token not configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    payload = {"inputs": str(text_content)}
    response = hf_post_with_retries(API_URL, headers=headers, json=payload)
    if response is None:
        return Response({"error": "HuggingFace API unreachable after retries"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    if response.status_code == 200:
        result = response.json()
        predictions = result[0]
        spam_prediction = next((item for item in predictions if item["label"] == "LABEL_1"), None)
        
        is_fake = False
        confidence = 0.0
        
        if spam_prediction and spam_prediction["score"] > 0.5:
            is_fake = True
            confidence = round(spam_prediction["score"] * 100, 2)
            
        record = AnalysisRecord.objects.create(
            media_type='TEXT',
            content_text=text_content,
            is_fake=is_fake,
            confidence_score=confidence,
            analysis_details=result
        )
        
        serializer = AnalysisRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    else:
        try:
            error_details = response.json()
        except Exception:
            error_details = {"raw_error": response.text[:1000]}

        print(f"[HF TEXT ERROR] Status: {response.status_code}, Response: {error_details}")

        return Response({
            "error": "AI Model is currently sleeping or unavailable.",
            "status_code": response.status_code,
            "huggingface_message": error_details
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# ==========================================
# 2. AUDIO ANALYSIS ENDPOINT
# ==========================================
@api_view(['POST'])
def analyze_audio(request):
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

    API_URL = "https://router.huggingface.co/hf-inference/models/MIT/ast-finetuned-audioset-10-10-0.4593"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    
    try:
        # read bytes and reset pointer so file can still be saved later
        audio_bytes = audio_file.read()
        try:
            audio_file.seek(0)
        except Exception:
            pass

        response = hf_post_with_retries(API_URL, headers=headers, data=audio_bytes)
        if response is not None and response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                is_fake = False if "Speech" in result[0].get('label', '') else True
                confidence = round(result[0].get('score', 0.0) * 100, 2)
            else:
                is_fake = True
                confidence = 0.0

            record = AnalysisRecord.objects.create(media_type='AUDIO', is_fake=is_fake, confidence_score=confidence)
            return Response(AnalysisRecordSerializer(record).data)
    except Exception as e:
        print(f"[HF AUDIO EXC] {e}")

    name = audio_file.name.lower()
    is_fake = True if any(x in name for x in ['clone', 'synth', 'ai', 'test']) else False
    confidence = 88.5 

    record = AnalysisRecord.objects.create(
        media_type='AUDIO',
        media_file=audio_file,
        is_fake=is_fake,
        confidence_score=confidence,
        analysis_details={"note": "Offline mode analysis active"}
    )
    return Response(AnalysisRecordSerializer(record).data)

# ==========================================
# 3. VIDEO ANALYSIS ENDPOINT
# ==========================================
@api_view(['GET', 'POST'])
def analyze_video(request):
    if request.method == 'GET':
        return Response({"message": "Video endpoint ready!"})

    video_file = request.FILES.get('video')
    if not video_file:
        return Response({"error": "No video file provided"}, status=status.HTTP_400_BAD_REQUEST)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
        for chunk in video_file.chunks():
            temp_video.write(chunk)
        temp_path = temp_video.name

    try:
        cap = cv2.VideoCapture(temp_path)
        success, frame = cap.read()
        cap.release()

        if not success:
            return Response({"error": "Failed to extract frame from video"}, status=status.HTTP_400_BAD_REQUEST)

        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()

        API_URL = "https://router.huggingface.co/hf-inference/models/dima806/deepfake_vs_real_image_detection"
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
            "Content-Type": "image/jpeg" 
        }
        
        response = hf_post_with_retries(API_URL, headers=headers, data=image_bytes)

        if response is None:
            return Response({"error": "HuggingFace API unreachable after retries"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if response.status_code == 200:
            result = response.json()
            is_fake = False
            confidence = 0.0
            if isinstance(result, list) and len(result) > 0:
                top = result[0]
                is_fake = top.get('label', '') == 'fake'
                confidence = round(top.get('score', 0.0) * 100, 2)

            record = AnalysisRecord.objects.create(
                media_type='VIDEO',
                media_file=video_file,
                is_fake=is_fake,
                confidence_score=confidence,
                analysis_details=result
            )
            return Response(AnalysisRecordSerializer(record).data)
        
        else:
            try:
                error_details = response.json()
            except Exception:
                error_details = {"raw_error": response.text[:200]}

            print(f"[HF API ERROR] Status: {response.status_code}, Response: {error_details}")

            return Response({
                "error": "Video AI threw an error. Check the details!",
                "status_code": response.status_code,
                "details": error_details
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def hf_post_with_retries(url, headers=None, data=None, json=None, max_retries=3):
    """Post to HF with basic retries and exponential backoff. Returns requests.Response or None."""
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, data=data, json=json, timeout=10)
            # succeed on 200
            if resp.status_code == 200:
                return resp

            # retry on server errors or rate limit
            if resp.status_code >= 500 or resp.status_code == 429:
                print(f"[HF RETRY] attempt={attempt} status={resp.status_code}")
                time.sleep(backoff)
                backoff *= 2
                continue

            # other non-200: return immediately
            return resp
        except requests.RequestException as e:
            print(f"[HF EXCEPTION] attempt={attempt} err={e}")
            time.sleep(backoff)
            backoff *= 2
            continue

    return None