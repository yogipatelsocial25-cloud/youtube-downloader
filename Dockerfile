FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deno.land/install.sh | sh

ENV DENO_INSTALL=/root/.deno
ENV PATH="/root/.deno/bin:$PATH"

COPY requirements.txt .

RUN python -m pip install --upgrade pip

RUN python -m pip install --no-cache-dir "yt-dlp[default]"

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

RUN python -m py_compile app.py

RUN python -c "import app; print('APP IMPORT SUCCESS')"

CMD ["sh", "-c", "gunicorn --workers 1 --timeout 300 --bind 0.0.0.0:$PORT app:app"]
