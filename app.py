import os
import uuid
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

download_status = {}


def progress_hook_factory(job_id):
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)

            percent = 0

            if total:
                percent = (downloaded / total) * 100

            download_status[job_id] = {
                "status": "downloading",
                "percent": round(percent, 1),
                "speed": d.get("_speed_str", ""),
                "eta": d.get("_eta_str", "")
            }

        elif d["status"] == "finished":
            download_status[job_id] = {
                "status": "processing",
                "percent": 100
            }

    return hook


def common_yt_options(job_id=None):

    options = {
        "noplaylist": True,

        "quiet": False,
        "no_warnings": False,

        "socket_timeout": 60,

        "retries": 10,
        "fragment_retries": 10,

        "continuedl": True,
        "overwrites": False,

        "concurrent_fragment_downloads": 4,

        "buffersize": 1024 * 1024,

        "http_chunk_size": 10 * 1024 * 1024,

        # YouTube JavaScript challenge solving
        "js_runtimes": {
            "deno": {}
        },

        # Download EJS challenge components
        "remote_components": {
            "ejs": "github"
        },

        # YouTube player clients
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android_vr",
                    "web"
                ]
            }
        }
    }

    if job_id:
        options["progress_hooks"] = [
            progress_hook_factory(job_id)
        ]

    return options


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "yt_dlp": yt_dlp.version.__version__
    })


@app.route("/create-job", methods=["POST"])
def create_job():

    job_id = str(uuid.uuid4())

    download_status[job_id] = {
        "status": "starting",
        "percent": 0
    }

    return jsonify({
        "success": True,
        "job_id": job_id
    })


@app.route("/progress/<job_id>")
def progress(job_id):

    return jsonify(
        download_status.get(
            job_id,
            {
                "status": "unknown",
                "percent": 0
            }
        )
    )


@app.route("/info", methods=["POST"])
def info():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        options = common_yt_options()
        options["skip_download"] = True

        with yt_dlp.YoutubeDL(options) as ydl:
            info_data = ydl.extract_info(
                url,
                download=False
            )

        return jsonify({
            "success": True,
            "title": info_data.get("title"),
            "thumbnail": info_data.get("thumbnail"),
            "duration": info_data.get("duration"),
            "channel": info_data.get("channel"),
            "uploader": info_data.get("uploader"),
            "view_count": info_data.get("view_count")
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/download/video", methods=["POST"])
def download_video():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()
    job_id = data.get("job_id") or str(uuid.uuid4())

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        job_dir = DOWNLOAD_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        output = str(
            job_dir / "%(title)s.%(ext)s"
        )

        options = common_yt_options(job_id)

        options.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": output
        })

        with yt_dlp.YoutubeDL(options) as ydl:

            info_data = ydl.extract_info(
                url,
                download=True
            )

            filename = ydl.prepare_filename(info_data)

        final_file = Path(filename)

        if not final_file.exists():

            mp4_file = final_file.with_suffix(".mp4")

            if mp4_file.exists():
                final_file = mp4_file

        if not final_file.exists():

            raise FileNotFoundError(
                "Downloaded video file was not found."
            )

        download_status[job_id] = {
            "status": "completed",
            "percent": 100
        }

        return send_file(
            final_file,
            as_attachment=True
        )

    except Exception as e:

        download_status[job_id] = {
            "status": "error",
            "error": str(e)
        }

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/download/audio", methods=["POST"])
def download_audio():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()
    job_id = data.get("job_id") or str(uuid.uuid4())

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        job_dir = DOWNLOAD_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        output = str(
            job_dir / "%(title)s.%(ext)s"
        )

        options = common_yt_options(job_id)

        options.update({
            "format": "bestaudio/best",
            "outtmpl": output,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ]
        })

        with yt_dlp.YoutubeDL(options) as ydl:

            info_data = ydl.extract_info(
                url,
                download=True
            )

            filename = ydl.prepare_filename(info_data)

        final_file = Path(filename).with_suffix(".mp3")

        if not final_file.exists():

            raise FileNotFoundError(
                "Downloaded audio file was not found."
            )

        download_status[job_id] = {
            "status": "completed",
            "percent": 100
        }

        return send_file(
            final_file,
            as_attachment=True
        )

    except Exception as e:

        download_status[job_id] = {
            "status": "error",
            "error": str(e)
        }

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/download/thumbnail", methods=["POST"])
def download_thumbnail():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        job_id = str(uuid.uuid4())

        job_dir = DOWNLOAD_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        output = str(
            job_dir / "%(title)s.%(ext)s"
        )

        options = common_yt_options()

        options.update({
            "skip_download": True,
            "writethumbnail": True,
            "outtmpl": output
        })

        with yt_dlp.YoutubeDL(options) as ydl:

            ydl.extract_info(
                url,
                download=True
            )

        image_files = [
            f for f in job_dir.iterdir()
            if f.is_file()
            and f.suffix.lower() in
            [".jpg", ".jpeg", ".png", ".webp"]
        ]

        if not image_files:

            raise FileNotFoundError(
                "Thumbnail was not found."
            )

        return send_file(
            image_files[0],
            as_attachment=True
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/download/details", methods=["POST"])
def download_details():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        options = common_yt_options()
        options["skip_download"] = True

        with yt_dlp.YoutubeDL(options) as ydl:

            info_data = ydl.extract_info(
                url,
                download=False
            )

        details = {
            "title": info_data.get("title"),
            "description": info_data.get("description"),
            "channel": info_data.get("channel"),
            "uploader": info_data.get("uploader"),
            "duration": info_data.get("duration"),
            "upload_date": info_data.get("upload_date"),
            "view_count": info_data.get("view_count"),
            "like_count": info_data.get("like_count"),
            "thumbnail": info_data.get("thumbnail"),
            "webpage_url": info_data.get("webpage_url")
        }

        return jsonify({
            "success": True,
            "details": details
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/download/all", methods=["POST"])
def download_all():

    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()
    job_id = data.get("job_id") or str(uuid.uuid4())

    if not url:
        return jsonify({
            "success": False,
            "error": "URL is required"
        }), 400

    try:

        job_dir = DOWNLOAD_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        output = str(
            job_dir / "%(title)s.%(ext)s"
        )

        options = common_yt_options(job_id)

        options.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "writethumbnail": True,
            "outtmpl": output
        })

        with yt_dlp.YoutubeDL(options) as ydl:

            ydl.extract_info(
                url,
                download=True
            )

        files = list(job_dir.iterdir())

        zip_path = job_dir / "download.zip"

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            for file in files:

                if file.is_file() and file.name != "download.zip":

                    zipf.write(
                        file,
                        arcname=file.name
                    )

        download_status[job_id] = {
            "status": "completed",
            "percent": 100
        }

        return send_file(
            zip_path,
            as_attachment=True,
            download_name="download.zip"
        )

    except Exception as e:

        download_status[job_id] = {
            "status": "error",
            "error": str(e)
        }

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        threaded=True
    )
