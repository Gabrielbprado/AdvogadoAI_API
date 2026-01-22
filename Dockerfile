# Container image for the AdvogadoAI API.
# Uses gunicorn with uvicorn workers to serve FastAPI.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# System deps for building wheels (bcrypt/Pillow), PDFs, and database drivers (MySQL/Azure SQL via pyodbc).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libpng-dev \
        libfreetype6-dev \
        libopenjp2-7 \
        curl \
        apt-transport-https \
        ca-certificates \
        gnupg \
        unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.asc.gpg \
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure default storage path exists (matches Settings.storage_dir default).
RUN mkdir -p /app/data/uploads

EXPOSE 8000

# Respect PORT if provided by the platform (e.g., Azure App Service / Container Apps).
ENV PORT=8000

CMD gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:${PORT} app.main:app
