FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir --upgrade python-magic

COPY . .

# Create required directories
RUN mkdir -p uploads logs

EXPOSE 5000

# Use Railway's PORT env var, default to 5000
ENV PORT=${PORT:-5000}

CMD ["/bin/sh", "-c", "echo 'PORT=$PORT' && echo 'Starting waitress...' && waitress-serve --host=0.0.0.0 --port=$PORT --threads=4 wsgi:app"]
