FROM python:3.12-slim

WORKDIR /app

# ============================================================
# SYSTEM PACKAGES
# ============================================================

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# INSTALL DENO
# ============================================================

RUN curl -fsSL https://deno.land/install.sh | sh

ENV DENO_INSTALL=/root/.deno
ENV PATH="/root/.deno/bin:$PATH"


# ============================================================
# PYTHON DEPENDENCIES
# ============================================================

COPY requirements.txt .

RUN python -m pip install --upgrade pip

RUN python -m pip install --no-cache-dir "yt-dlp[default]"

RUN python -m pip install --no-cache-dir -r requirements.txt


# ============================================================
# COPY APPLICATION
# ============================================================

COPY . .


# ============================================================
# DOWNLOAD DIRECTORY
# ============================================================

RUN mkdir -p downloads


# ============================================================
# START FLASK WITH GUNICORN
# ============================================================

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]
