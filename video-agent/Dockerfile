# Ready-made environment for the reel job: system tools, Node 22, Python 3.11 and the Python packages are installed ONCE here,
# so a run starts in seconds instead of spending minutes on apt and pip. Built by .github/workflows/video-image.yml.
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git gnupg ffmpeg fonts-noto-core espeak-ng \
      libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libxkbcommon0 libxfixes3 \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/reqs
COPY requirements.txt requirements-kokoro.txt ./
RUN pip install -r requirements.txt \
 && (pip install -r requirements-kokoro.txt || echo "kokoro not installed: edge-tts will be used")
