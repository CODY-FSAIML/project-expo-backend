# test_upload.py
import requests

# 1. The URL of your new Django endpoint
url = "http://127.0.0.1:8000/api/analyze-audio/"

# 2. Open the audio file in 'rb' (read-binary) mode
# Make sure the filename matches the file you pasted in your folder!
file_path = "sample.wav" 

try:
    with open(file_path, "rb") as audio_file:
        # 3. Package the file exactly how React will package it (with the key 'audio')
        files = {"audio": audio_file}
        
        print(f"Sending {file_path} to the AI... Please wait...")
        
        # 4. POST it to Django!
        response = requests.post(url, files=files)
        
        # 5. Print the result
        print("\n--- AI Analysis Result ---")
        print("Status Code:", response.status_code)
        print("Data:", response.json())

except FileNotFoundError:
    print(f"Error: Could not find '{file_path}'. Make sure it is in the same folder as this script!")