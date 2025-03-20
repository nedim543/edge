# Basis-Image
FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Abhängigkeiten kopieren und installieren
# COPY requirements.txt .
RUN pip install Flask requests
RUN pip install kubernetes flask

# App-Code kopieren
COPY edgeNode.py .

# Environment-Variablen setzen
ENV FLASK_APP=edgeNode.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_PORT=5000 
ENV NAME=node-default  

# Standardport für die App
EXPOSE 5000

# Flask-App ausführen
CMD ["python3", "./edgeNode.py"]