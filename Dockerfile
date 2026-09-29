FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates openssl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Сертификаты Минцифры (нужны для TLS к platform-api2.max.ru).
# Кладём их и в системное хранилище доверия, чтобы работало независимо от того,
# как код грузит certs/ (файлы .cer могут быть DER или PEM).
COPY certs/ /tmp/certs/
RUN set -e; \
    for f in /tmp/certs/*.cer /tmp/certs/*.crt /tmp/certs/*.pem; do \
      [ -e "$f" ] || continue; \
      n=$(basename "${f%.*}"); \
      openssl x509 -inform DER -in "$f" -out "/usr/local/share/ca-certificates/$n.crt" 2>/dev/null \
      || openssl x509 -inform PEM -in "$f" -out "/usr/local/share/ca-certificates/$n.crt"; \
    done; \
    update-ca-certificates; \
    rm -rf /tmp/certs

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

COPY . .

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

CMD ["python", "run_bot.py"]
