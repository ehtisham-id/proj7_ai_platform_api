FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system packages required to build some Python wheels (Pillow, numpy, opencv, psycopg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app
COPY ./alembic ./alembic

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

# Use uvicorn without --reload for container run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
