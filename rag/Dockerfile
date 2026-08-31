FROM python:3.10-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier et installer les dépendances Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY app/ ./app/
COPY data/ ./data/

# Variables d'environnement
ENV PYTHONPATH=/app
ENV TESSERACT_CMD=/usr/bin/tesseract

# Port exposé
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]