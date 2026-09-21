import os
import re
import shutil
import zipfile
import uuid
import threading
import time

from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DOWNLOAD STATUS
# ============================================================

download_status = {}
status_lock = threading.Lock()


def create_job():
    job_id = uuid.uuid4().hex

    with status_lock:
        download_status[job_id] = {
            "status": "starting",
            "progress": 0,
            "speed": "",
            "eta": "",
            "elapsed": 0,
            "message": "Starting download...",
            "started_at": time.time()
        }

    return job_id


def update_job(job_id, **kwargs):
    if not job_id:
        return

    with status_lock:
        if job_id not in download_status:
            download_status[job_id] = {}

        download_status[job_id].update(kwargs)


def get_job(job_id):
    with status_lock:

        data = download_status.get(
            job_id,
            {
                "status": "unknown",
                "progress": 0,
                "speed": "",
                "eta": "",
                "elapsed": 0,
                "message": ""
            }
        )

        data = dict(data)

        # Calculate real elapsed time on server
        if data.get("started_at"):
            if data.get("status") not in [
                "completed",
                "error"
            ]:
                data["elapsed"] = int(
                    time.time() - data["started_at"]
                )

        return data


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(name):
    """
    Make a Windows-safe filename/folder name.
    """

    name = str(name or "YouTube Video")

    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        '',
        name
    )

    name = name.strip().rstrip(".")

    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9"
    }

    if name.upper() in reserved:
        name = "_" + name

    if not name:
        name = "YouTube Video"

    return name[:150]


# ============================================================
# VIDEO INFORMATION
# ============================================================

def get_video_info(url):

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "retries": 3
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(
            url,
            download=False
        )


# ============================================================
# QUALITY DETECTION
# ============================================================

def get_available_qualities(info):

    quality_list = set()

    for fmt in info.get("formats", []):

        height = fmt.get("height")

        if height:

            try:
                quality_list.add(int(height))
            except Exception:
                pass

    standard_qualities = [
        360,
        480,
        720,
        1080,
        1440,
        2160
    ]

    available = []

    for quality in standard_qualities:

        if any(
            h >= quality
            for h in quality_list
        ):
            available.append(quality)

    return available


# ============================================================
# VIDEO FOLDER
# ============================================================

def get_video_folder(info):

    title = safe_filename(
        info.get(
            "title",
            "YouTube Video"
        )
    )

    folder = DOWNLOAD_DIR / title

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return title, folder


# ============================================================
# DURATION
# ============================================================

def format_duration(seconds):

    if not seconds:
        return "00:00"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# FIND FILE
# ============================================================

def find_file(folder, pattern):

    files = list(folder.glob(pattern))

    if not files:
        return None

    return max(
        files,
        key=lambda f: f.stat().st_mtime
    )


# ============================================================
# DOWNLOAD PROGRESS HOOK
# ============================================================

def progress_hook(job_id):

    def hook(data):

        try:

            status = data.get("status")

            if status == "downloading":

                percent_text = data.get(
                    "_percent_str",
                    "0%"
                )

                speed = data.get(
                    "_speed_str",
                    ""
                )

                eta = data.get(
                    "_eta_str",
                    ""
                )

                elapsed = data.get(
                    "elapsed",
                    0
                )

                try:

                    percent = float(
                        percent_text
                        .replace("%", "")
                        .strip()
                    )

                except Exception:

                    percent = 0

                update_job(
                    job_id,
                    status="downloading",
                    progress=percent,
                    speed=speed,
                    eta=eta,
                    elapsed=elapsed,
                    message="Downloading..."
                )

            elif status == "finished":

                update_job(
                    job_id,
                    progress=100,
                    status="processing",
                    message="Processing file..."
                )

        except Exception:
            pass

    return hook


# ============================================================
# FAST YT-DLP OPTIONS
# ============================================================

def base_fast_options(job_id=None):

    options = {

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        # Concurrent fragments
        "concurrent_fragment_downloads": 8,

        # Network
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 20,

        # Buffer
        "buffersize": 1024 * 1024,

        # Resume downloads
        "continuedl": True,

        # Don't overwrite
        "overwrites": False,

        # HTTP chunk
        "http_chunk_size": 10 * 1024 * 1024
    }

    if job_id:

        options["progress_hooks"] = [
            progress_hook(job_id)
        ]

    return options


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# CREATE JOB
# ============================================================

@app.route(
    "/create-job",
    methods=["POST"]
)
def create_download_job():

    job_id = create_job()

    return jsonify({
        "success": True,
        "job_id": job_id
    })


# ============================================================
# GET JOB STATUS
# ============================================================

@app.route(
    "/progress/<job_id>",
    methods=["GET"]
)
def progress(job_id):

    return jsonify(
        get_job(job_id)
    )


# ============================================================
# VIDEO INFORMATION
# ============================================================

@app.route(
    "/info",
    methods=["POST"]
)
def video_info():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "error": "Invalid request."
            }), 400

        url = data.get(
            "url",
            ""
        ).strip()

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "Please enter a YouTube URL."
            }), 400

        info = get_video_info(url)

        title = info.get(
            "title",
            "YouTube Video"
        )

        thumbnail = info.get(
            "thumbnail",
            ""
        )

        duration = info.get(
            "duration",
            0
        )

        uploader = info.get(
            "uploader",
            ""
        )

        channel = info.get(
            "channel",
            uploader
        )

        qualities = get_available_qualities(
            info
        )

        return jsonify({

            "success": True,

            "title": title,

            "thumbnail": thumbnail,

            "duration": duration,

            "uploader": uploader,

            "channel": channel,

            "qualities": qualities,

            "url": url
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DOWNLOAD VIDEO
# ============================================================

@app.route(
    "/download/video",
    methods=["POST"]
)
def download_video():

    job_id = None

    try:

        data = request.get_json() or {}

        url = data.get(
            "url",
            ""
        ).strip()

        quality = int(
            data.get(
                "quality",
                720
            )
        )

        job_id = data.get(
            "job_id"
        )

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "YouTube URL is required."
            }), 400

        if not job_id:
            job_id = create_job()

        update_job(
            job_id,
            status="starting",
            progress=0,
            message="Getting video information..."
        )

        info = get_video_info(url)

        title, video_folder = get_video_folder(
            info
        )

        output_template = str(
            video_folder /
            f"{title} - {quality}p.%(ext)s"
        )

        ydl_opts = {
    "format": "bestvideo*+bestaudio/best",
    "merge_output_format": "mp4",

    "outtmpl": str(download_path),

    "noplaylist": True,

    "quiet": False,
    "no_warnings": False,

    "js_runtimes": {
        "deno": {}
    },

    "remote_components": {
        "ejs": "github"
    },

    "retries": 3,
    "fragment_retries": 3,
}

        ydl_opts.update({

            "format": (
                f"bestvideo[height<={quality}]"
                f"+bestaudio/"
                f"best[height<={quality}]"
            ),

            "outtmpl":
                output_template,

            "merge_output_format":
                "mp4",

            "postprocessor_args": {
                "ffmpeg": [
                    "-threads",
                    "0"
                ]
            }
        })

        update_job(
            job_id,
            status="downloading",
            message=
                f"Downloading {quality}p video..."
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])

        video_file = find_file(
            video_folder,
            f"{title} - {quality}p.mp4"
        )

        if video_file is None:

            video_file = find_file(
                video_folder,
                f"{title} - {quality}p.*"
            )

        if video_file is None:

            update_job(
                job_id,
                status="error",
                message=
                    "Video file not found."
            )

            return jsonify({
                "success": False,
                "error":
                    "Video was downloaded but MP4 file could not be found."
            }), 500

        elapsed = int(
            time.time()
            -
            download_status[job_id]["started_at"]
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            elapsed=elapsed,
            message="Video download completed."
        )

        return send_file(
            video_file,
            as_attachment=True,
            download_name=video_file.name
        )

    except Exception as e:

        update_job(
            job_id,
            status="error",
            message=str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DOWNLOAD AUDIO
# ============================================================

@app.route(
    "/download/audio",
    methods=["POST"]
)
def download_audio():

    job_id = None

    try:

        data = request.get_json() or {}

        url = data.get(
            "url",
            ""
        ).strip()

        job_id = data.get(
            "job_id"
        )

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "YouTube URL is required."
            }), 400

        if not job_id:
            job_id = create_job()

        update_job(
            job_id,
            status="starting",
            progress=0,
            message="Preparing audio..."
        )

        info = get_video_info(url)

        title, video_folder = get_video_folder(
            info
        )

        output_template = str(
            video_folder /
            f"{title} - Audio.%(ext)s"
        )

        ydl_opts = {
    "format": "bestvideo*+bestaudio/best",
    "merge_output_format": "mp4",

    "outtmpl": str(download_path),

    "noplaylist": True,

    "quiet": False,
    "no_warnings": False,

    "js_runtimes": {
        "deno": {}
    },

    "remote_components": {
        "ejs": "github"
    },

    "retries": 3,
    "fragment_retries": 3,
}

        ydl_opts.update({

            "format":
                "bestaudio/best",

            "outtmpl":
                output_template,

            "postprocessors": [
                {
                    "key":
                        "FFmpegExtractAudio",

                    "preferredcodec":
                        "mp3",

                    "preferredquality":
                        "192"
                }
            ],

            "postprocessor_args": {
                "ffmpeg": [
                    "-threads",
                    "0"
                ]
            }
        })

        update_job(
            job_id,
            status="downloading",
            message="Downloading audio..."
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])

        audio_file = (
            video_folder /
            f"{title} - Audio.mp3"
        )

        if not audio_file.exists():

            audio_file = find_file(
                video_folder,
                f"{title} - Audio.*"
            )

        if audio_file is None:

            update_job(
                job_id,
                status="error",
                message="Audio file could not be found."
            )

            return jsonify({
                "success": False,
                "error":
                    "Audio file could not be found."
            }), 500

        elapsed = int(
            time.time()
            -
            download_status[job_id]["started_at"]
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            elapsed=elapsed,
            message="Audio download completed."
        )

        return send_file(
            audio_file,
            as_attachment=True,
            download_name=audio_file.name
        )

    except Exception as e:

        update_job(
            job_id,
            status="error",
            message=str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DOWNLOAD THUMBNAIL
# ============================================================

@app.route(
    "/download/thumbnail",
    methods=["POST"]
)
def download_thumbnail():

    job_id = None

    try:

        data = request.get_json() or {}

        url = data.get(
            "url",
            ""
        ).strip()

        job_id = data.get(
            "job_id"
        )

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "YouTube URL is required."
            }), 400

        if not job_id:
            job_id = create_job()

        update_job(
            job_id,
            status="starting",
            progress=0,
            message="Downloading thumbnail..."
        )

        info = get_video_info(url)

        title, video_folder = get_video_folder(
            info
        )

        thumbnail_url = info.get(
            "thumbnail"
        )

        if not thumbnail_url:

            return jsonify({
                "success": False,
                "error":
                    "Thumbnail not available."
            }), 404

        output_template = str(
            video_folder /
            f"{title} - Thumbnail.%(ext)s"
        )

       ydl_opts = {
    "format": "bestvideo*+bestaudio/best",
    "merge_output_format": "mp4",

    "outtmpl": str(download_path),

    "noplaylist": True,

    "quiet": False,
    "no_warnings": False,

    "js_runtimes": {
        "deno": {}
    },

    "remote_components": {
        "ejs": "github"
    },

    "retries": 3,
    "fragment_retries": 3,
}

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download([url])

        thumbnail_file = find_file(
            video_folder,
            f"{title} - Thumbnail.*"
        )

        if thumbnail_file is None:

            update_job(
                job_id,
                status="error",
                message="Thumbnail file could not be found."
            )

            return jsonify({
                "success": False,
                "error":
                    "Thumbnail file could not be found."
            }), 500

        elapsed = int(
            time.time()
            -
            download_status[job_id]["started_at"]
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            elapsed=elapsed,
            message="Thumbnail downloaded."
        )

        return send_file(
            thumbnail_file,
            as_attachment=True,
            download_name=thumbnail_file.name
        )

    except Exception as e:

        update_job(
            job_id,
            status="error",
            message=str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DETAILS DOCUMENT
# ============================================================

def create_details_file(
    info,
    title,
    video_folder,
    quality
):

    duration = format_duration(
        info.get(
            "duration",
            0
        )
    )

    description = info.get(
        "description",
        ""
    )

    details_file = (
        video_folder /
        f"{title} - Details.txt"
    )

    details_content = f"""
============================================================
                    VIDEO DETAILS
============================================================

Title:

{title}

Channel:

{info.get("channel", "Unknown")}

Uploader:

{info.get("uploader", "Unknown")}

YouTube URL:

{info.get("webpage_url", "")}

Video ID:

{info.get("id", "Unknown")}

Duration:

{duration}

Selected Video Quality:

{quality}p

Upload Date:

{info.get("upload_date", "Unknown")}

Views:

{info.get("view_count", "Unknown")}

Likes:

{info.get("like_count", "Unknown")}

Thumbnail URL:

{info.get("thumbnail", "")}

Downloaded:

{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


============================================================
                    DOWNLOADED FILES
============================================================

Video:

{title} - {quality}p.mp4

Audio:

{title} - Audio.mp3

Thumbnail:

{title} - Thumbnail.jpg

Details:

{title} - Details.txt


============================================================
                    DESCRIPTION
============================================================

{description}

============================================================
"""

    with open(
        details_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            details_content.strip()
        )

    return details_file


# ============================================================
# DOWNLOAD DETAILS
# ============================================================

@app.route(
    "/download/details",
    methods=["POST"]
)
def download_details():

    job_id = None

    try:

        data = request.get_json() or {}

        url = data.get(
            "url",
            ""
        ).strip()

        quality = int(
            data.get(
                "quality",
                720
            )
        )

        job_id = data.get(
            "job_id"
        )

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "YouTube URL is required."
            }), 400

        if not job_id:
            job_id = create_job()

        update_job(
            job_id,
            status="starting",
            progress=0,
            message="Creating details document..."
        )

        info = get_video_info(url)

        title, video_folder = get_video_folder(
            info
        )

        details_file = create_details_file(
            info,
            title,
            video_folder,
            quality
        )

        elapsed = int(
            time.time()
            -
            download_status[job_id]["started_at"]
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            elapsed=elapsed,
            message="Details document created."
        )

        return send_file(
            details_file,
            as_attachment=True,
            download_name=details_file.name
        )

    except Exception as e:

        update_job(
            job_id,
            status="error",
            message=str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DOWNLOAD ALL
# ============================================================

@app.route(
    "/download/all",
    methods=["POST"]
)
def download_all():

    job_id = None

    try:

        data = request.get_json() or {}

        url = data.get(
            "url",
            ""
        ).strip()

        quality = int(
            data.get(
                "quality",
                720
            )
        )

        job_id = data.get(
            "job_id"
        )

        if not url:

            return jsonify({
                "success": False,
                "error":
                    "YouTube URL is required."
            }), 400

        if not job_id:
            job_id = create_job()

        update_job(
            job_id,
            status="starting",
            progress=0,
            message="Preparing all files..."
        )

        info = get_video_info(url)

        title, video_folder = get_video_folder(
            info
        )

        # ====================================================
        # 1. VIDEO
        # ====================================================

        update_job(
            job_id,
            status="downloading",
            progress=0,
            message=
                f"Downloading {quality}p video..."
        )

        video_path = find_file(
            video_folder,
            f"{title} - {quality}p.mp4"
        )

        if video_path is None:

            output_template = str(
                video_folder /
                f"{title} - {quality}p.%(ext)s"
            )

            video_options = base_fast_options(
                job_id
            )

            video_options.update({

                "format": (
                    f"bestvideo[height<={quality}]"
                    f"+bestaudio/"
                    f"best[height<={quality}]"
                ),

                "outtmpl":
                    output_template,

                "merge_output_format":
                    "mp4",

                "postprocessor_args": {
                    "ffmpeg": [
                        "-threads",
                        "0"
                    ]
                }
            })

            with yt_dlp.YoutubeDL(
                video_options
            ) as ydl:

                ydl.download([url])

            video_path = find_file(
                video_folder,
                f"{title} - {quality}p.mp4"
            )

        if video_path is None:

            return jsonify({
                "success": False,
                "error":
                    "Video download failed."
            }), 500

        # ====================================================
        # 2. AUDIO
        # ====================================================

        update_job(
            job_id,
            progress=0,
            status="downloading",
            message="Downloading audio..."
        )

        audio_path = (
            video_folder /
            f"{title} - Audio.mp3"
        )

        if not audio_path.exists():

            audio_options = base_fast_options(
                job_id
            )

            audio_options.update({

                "format":
                    "bestaudio/best",

                "outtmpl":
                    str(
                        video_folder /
                        f"{title} - Audio.%(ext)s"
                    ),

                "postprocessors": [
                    {
                        "key":
                            "FFmpegExtractAudio",

                        "preferredcodec":
                            "mp3",

                        "preferredquality":
                            "192"
                    }
                ],

                "postprocessor_args": {
                    "ffmpeg": [
                        "-threads",
                        "0"
                    ]
                }
            })

            with yt_dlp.YoutubeDL(
                audio_options
            ) as ydl:

                ydl.download([url])

        audio_path = find_file(
            video_folder,
            f"{title} - Audio.*"
        )

        # ====================================================
        # 3. THUMBNAIL
        # ====================================================

        update_job(
            job_id,
            progress=0,
            message="Downloading thumbnail..."
        )

        thumbnail_path = find_file(
            video_folder,
            f"{title} - Thumbnail.*"
        )

        if thumbnail_path is None:

            thumbnail_options = {

                "skip_download": True,

                "writethumbnail": True,

                "outtmpl":
                    str(
                        video_folder /
                        f"{title} - Thumbnail.%(ext)s"
                    ),

                "noplaylist": True,

                "quiet": True,

                "retries": 3
            }

            with yt_dlp.YoutubeDL(
                thumbnail_options
            ) as ydl:

                ydl.download([url])

            thumbnail_path = find_file(
                video_folder,
                f"{title} - Thumbnail.*"
            )

        # ====================================================
        # 4. DETAILS
        # ====================================================

        update_job(
            job_id,
            progress=0,
            message="Creating details document..."
        )

        details_path = (
            video_folder /
            f"{title} - Details.txt"
        )

        if not details_path.exists():

            details_path = create_details_file(
                info,
                title,
                video_folder,
                quality
            )

        # ====================================================
        # 5. CREATE ZIP
        # ====================================================

        update_job(
            job_id,
            progress=95,
            status="processing",
            message="Creating ZIP package..."
        )

        zip_path = (
            DOWNLOAD_DIR /
            f"{title}.zip"
        )

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            for file_path in video_folder.iterdir():

                if file_path.is_file():

                    archive_name = (
                        Path(title) /
                        file_path.name
                    )

                    zip_file.write(
                        file_path,
                        archive_name
                    )

        elapsed = int(
            time.time()
            -
            download_status[job_id]["started_at"]
        )

        update_job(
            job_id,
            status="completed",
            progress=100,
            elapsed=elapsed,
            message="All files completed."
        )

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=
                f"{title}.zip"
        )

    except Exception as e:

        update_job(
            job_id,
            status="error",
            message=str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("YouTube Downloader - FAST MODE")
    print("=" * 60)

    print(
        f"Download folder: {DOWNLOAD_DIR}"
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=True
    )
