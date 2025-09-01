from flask import Flask, render_template, request, jsonify, Response
import yt_dlp
import os
import json
import time
import threading

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
progress_data = {}

def download_video(url, format_id):
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'format': format_id,
        'progress_hooks': [progress_hook],
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def progress_hook(d):
    global progress_data
    filename = d.get('filename', 'unknown')
    if d['status'] == 'downloading':
        progress_data[filename] = {
            'percent': d.get('_percent_str', '0%').strip(),
            'speed': d.get('_speed_str', 'N/A'),
            'eta': d.get('_eta_str', 'N/A'),
            'size': d.get('_total_bytes_str', 'N/A'),
            'fragments': d.get('fragment_index', 'N/A'),
        }
    elif d['status'] == 'finished':
        progress_data[filename]['percent'] = "100%"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_formats', methods=['POST'])
def get_formats():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "URL is required."})

    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {
                    "format_id": f["format_id"],
                    "resolution": f.get("resolution") or f.get("height", "Unknown"),
                    "ext": f["ext"]
                }
                for f in info.get("formats", [])
                if f.get("resolution") or f.get("height")
            ]
        return jsonify(formats)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format")
    if not url or not format_id:
        return jsonify({"error": "URL and format are required."})

    threading.Thread(target=download_video, args=(url, format_id)).start()
    return jsonify({"message": "Download started."})

@app.route('/progress')
def progress():
    def event_stream():
        while True:
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True)