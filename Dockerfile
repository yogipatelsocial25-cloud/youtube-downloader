FROM python:3.12-slim

WORKDIR /app

# System packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno
RUN curl -fsSL https://deno.land/install.sh | sh

ENV DENO_INSTALL=/root/.deno
ENV PATH=/root/.deno/bin:$PATH

# Copy project
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create download directory
RUN mkdir -p downloads

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]
