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

# Wait for DB and initialize
HEALTHCHECK --interval=5s --timeout=3s --retries=5 \
  CMD python -c "import psycopg2; psycopg2.connect('postgresql://dms_user:1234@db:5432/document_management')" || exit 1

EXPOSE 5000

CMD ["/bin/sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-5000} wsgi:app"]
