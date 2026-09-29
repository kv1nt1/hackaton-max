FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости отдельным слоем — пересобираются только при изменении requirements.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY run_bot.py .
COPY app ./app
COPY scripts ./scripts
COPY certs ./certs

RUN useradd --create-home --uid 1000 bot
USER bot

CMD ["python", "run_bot.py"]
