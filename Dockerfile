# Use an official Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /celebi

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    wget \
    unzip \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clone project files into the container
ARG REPO='https://github.com/HeIsOdin/Pokemon.git'
ARG BRANCH='celebi'
RUN git clone --single-branch --branch $BRANCH $REPO /pidgeotto

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Run the app
CMD ["python", "celebi.py"]