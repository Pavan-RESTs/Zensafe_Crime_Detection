from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import requests
from makepred import main

app = Flask(__name__)


mongo_uri = "mongodb+srv://diva:divakar2004@divacluster.4zroa.mongodb.net/UrbanGuard"
print("--> Connecting to MongoDB...")
client = MongoClient(mongo_uri)
db = client["UrbanGuard"]
alerts_collection = db["alerts"]
print("--> Connected to MongoDB")


UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def detect_anomaly(video_path):
    """
    Simulate anomaly detection logic.
    Replace this placeholder with actual ML model logic.
    """
    input_video_path = video_path

    pred = main(input_video_path)
    if (pred == 1):
        return True
    return False



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)  
    
    
    url = f"http://192.168.184.53:5005/uploads/{filename}" 
    return jsonify({'message': 'File uploaded successfully', 'url': url}), 200



@app.route('/uploads/<filename>', methods=['GET'])
def get_file(filename):
    print(f"Request to fetch file: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



@app.route('/analyze', methods=['POST'])
def analyze_video():
    print("--> Received a request")

    
    if 'video' not in request.files:
        print("No video file provided in the request.")
        return jsonify({'error': 'No video file provided'}), 400

    
    video = request.files['video']
    video_path = os.path.join('./uploaded_videos', video.filename)
    os.makedirs('./uploaded_videos', exist_ok=True)
    video.save(video_path)

    
    print(">>> Performing anomaly detection")
    anomaly_detected = detect_anomaly(video_path)
    print(">>> Anomaly detected: ", anomaly_detected)

    
    if anomaly_detected:
        
        video_url = upload_video_to_localhost(video_path)
        if video_url:
            alert_data = {
                "alert": True,
                "footageUrl": video_url,
                "location": request.form['location'],
                "anomalyDate": request.form['anomalyDate'],
                "anomalyTime": request.form['anomalyTime'],
                "coordinates": request.form['coordinates']
            }
            print(f"--> Inserting alert data into MongoDB: {alert_data}")
            alerts_collection.insert_one(alert_data)
            print("--> Alert data inserted into MongoDB")
        else:
            print("Failed to upload video for shareable URL.")

    
    print(f"--> Returning response: {{'anomaly': {anomaly_detected}}}")
    print("-------------------------------------------------------------------------------------------------------------------------------------------------------------")
    os.remove(video_path)
    return jsonify({'anomaly': anomaly_detected})



def upload_video_to_localhost(file_path):
    """Uploads a video to the local Flask server and returns the shareable URL."""
    url = 'http://192.168.184.53:5005/upload' 
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(url, files=files)
            if response.status_code == 200:
                return response.json().get('url')
            else:
                print("Failed to upload. Server response:", response.json())
    except Exception as e:
        print("Error:", e)
    return None


if __name__ == '__main__':
    print("--> Starting Flask server...")
    app.run(host='0.0.0.0', port=5005, debug=False)
