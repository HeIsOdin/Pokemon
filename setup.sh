#!/bin/bash

echo "=== Checking for Python ==="
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed."
    echo "Please install it using your package manager."
    exit 1
fi

echo "Python version: $(python3 --version)"

echo "=== Checking GitHub availability ==="
curl -s --head https://api.github.com | head -n 1 | grep "200 OK" > /dev/null
if [ $? -ne 0 ]; then
    echo "Cannot reach GitHub. Please check your internet connection or proxy."
    exit 1
fi

if [ -n "$GITHUB_TOKEN" ]; then
    echo "Found GITHUB_TOKEN. Verifying access..."
    response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user)
    login=$(echo "$response" | grep -o '"login": *"[^"]*"' | cut -d '"' -f4)

    if [ -z "$login" ]; then
        echo "GitHub token is invalid or unauthorized."
        exit 1
    fi

    echo "GitHub access verified as user: $login"
else
    echo "No GitHub token provided. Proceeding with unauthenticated access."
fi

echo "=== Cloning GitHub repository ==="
if [ ! -d "Pokemon" ]; then
    git clone https://github.com/HeIsOdin/Pokemon
    if [ $? -ne 0 ]; then
        echo "Failed to clone repository."
        exit 1
    fi
else
    echo "Repository already exists. Skipping clone."
fi

cd Pokemon

echo "=== Checking for kaggle.json ==="
KAGGLE_JSON="$HOME/.kaggle/kaggle.json"
if [ ! -f "$KAGGLE_JSON" ]; then
    echo "kaggle.json not found at $KAGGLE_JSON"
    echo "Download it from https://www.kaggle.com/account and place it in ~/.kaggle"
    exit 1
fi

echo "Validating kaggle.json contents..."
if ! python3 -c "
import json, sys
try:
    with open('$KAGGLE_JSON') as f:
        data = json.load(f)
        if not data.get('username') or not data.get('key'):
            sys.exit(1)
except:
    sys.exit(1)
"; then
    echo "kaggle.json is malformed or missing required fields (username, key)."
    exit 1
else
    echo "kaggle.json is valid and ready to use."
fi

echo "=== Checking for PostgreSQL ==="
if command -v psql > /dev/null 2>&1; then
    echo "PostgreSQL is installed: $(psql --version)"
else
    echo "PostgreSQL is not installed."

    echo "Checking for Docker..."
    if ! command -v docker > /dev/null 2>&1; then
        echo "Docker is not installed. Please install PostgreSQL manually or install Docker to run it in a container."
        exit 1
    fi

    echo "Docker is installed. Checking for running PostgreSQL containers..."
    if docker ps --filter "ancestor=postgres" --format '{{.Names}}' | grep -q .; then
        echo "A PostgreSQL container is currently running."
    elif docker images --format '{{.Repository}}' | grep -q '^postgres$'; then
        echo "A PostgreSQL image exists. You can run it with:"
        echo "  docker run --name pg_container -e POSTGRES_PASSWORD=yourpassword -d -p 5432:5432 postgres"
    else
        echo "No PostgreSQL container or image found."
        echo "You can pull and run it with:"
        echo "  docker pull postgres"
        echo "  docker run --name pg_container -e POSTGRES_PASSWORD=yourpassword -d -p 5432:5432 postgres"
        exit 1
    fi
fi

VENV="PyPikachu"
echo "=== Creating virtual environment '$VENV' ==="
python3 -m venv $VENV
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment"
    exit 1
fi

echo "=== Activating virtual environment ==="
source $VENV/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

echo "=== Upgrading pip ==="
pip install --upgrade pip

if [ -f requirements.txt ]; then
    echo "=== Installing dependencies from requirements.txt ==="
    pip install -r requirements.txt
else
    echo "No requirements.txt file found."
fi

echo "=== Setup complete. Project is ready. ==="

echo "=== Ensuring logs directory exists ==="
mkdir -p logs

echo "=== Launching setup.py, app.py, and messenger.py concurrently ==="
nohup python setup.py > logs/setup.log 2>&1 &
nohup python app.py > logs/app.log 2>&1 &
nohup python messenger.py > logs/messenger.log 2>&1 &

echo "All scripts running in background. Logs are in the 'logs/' directory."
jobs
