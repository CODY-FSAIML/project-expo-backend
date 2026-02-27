import requests

url = "http://127.0.0.1:8000/api/analyze-video/"
file_path = "sample.mp4" 

try:
    with open(file_path, "rb") as video_file:
        files = {"video": video_file}
        print(f"Sending {file_path} to Django...")
        print("Extracting frame and talking to AI... This might take 10-20 seconds!")
        
        response = requests.post(url, files=files)
        
        print("\n--- Video Analysis Result ---")
        print("Status Code:", response.status_code)
        print("Data:", response.json())
        
except FileNotFoundError:
    print("Error: Could not find 'sample.mp4'. Make sure it is in the same folder!")
except Exception as e:
    print(f"Error: {e}")