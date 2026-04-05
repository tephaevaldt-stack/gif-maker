FROM python:3.11-slim

# Install ffmpeg and yt-dlp system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp via pip (always latest)
RUN pip install --no-cache-dir yt-dlp

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

EXPOSE $PORT

CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 2
