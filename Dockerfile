FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg postgresql-client ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
RUN useradd --create-home --uid 10001 botuser && mkdir -p /tmp/telegram-media-bot && chown -R botuser:botuser /app /tmp/telegram-media-bot
USER botuser
CMD ["python", "-m", "app.main"]
