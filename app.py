from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import yt_dlp
import os
import time
import json

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

download_progress = {}  # Dictionary to store progress for each download

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.form["url"]
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                {
                    "format_id": f["format_id"],
                    "resolution": f.get("resolution", "N/A"),
                    "ext": f["ext"]
                }
                for f in info["formats"] if f.get("resolution")
            ]
        return jsonify(formats)
    except Exception as e:
        return jsonify({"error": str(e)})

def progress_hook(d):
    if d['status'] == 'downloading':
        download_progress[d['filename']] = d['_percent_str']
    elif d['status'] == 'finished':
        download_progress[d['filename']] = '100%'

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    format_id = request.form["format"]
    try:
        ydl_opts = {
            'format': f'{format_id}+bestaudio',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            filename = os.path.basename(filename)

        return jsonify({"filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/progress")
def progress():
    def generate():
        while True:
            progress_data = json.dumps(download_progress)  # Use json.dumps instead of jsonify
            yield f"data: {progress_data}\n\n"
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')

@app.route("/downloads/<filename>")
def get_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
