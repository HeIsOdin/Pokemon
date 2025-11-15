FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /zapdos

ARG REPO='https://github.com/HeIsOdin/Pokemon.git'
ARG BRANCH='zapdos'

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git

RUN git clone --single-branch -b ${BRANCH} ${REPO} /zapdos \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p flask_sessions logs

ENV FLASK_PORT=5000

EXPOSE 5000

CMD ["python", "zapdos.py"]
