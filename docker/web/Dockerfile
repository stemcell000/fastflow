FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    libldap-common \
    libsasl2-2 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# setuptools en premier, dans le système, avant tout le reste
RUN pip install --upgrade pip && \
    pip install --upgrade setuptools && \
    pip install --upgrade wheel

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY backend/ .

# Entrypoint
COPY docker/web/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Répertoires pour les fichiers générés
RUN mkdir -p /app/staticfiles /app/media /app/celerybeat

# Utilisateur non-root
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]