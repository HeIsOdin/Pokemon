from flask import Flask, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_session import Session
from datetime import timedelta
from flask_cors import CORS

import json
import datetime
import subprocess
import requests
import os
import time
import rotom
import re
import bcrypt
import logging

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://heisodin.github.io"])
(app.secret_key,) = rotom.enviromentals('FLASK_SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_sessions')
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True
)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=100)
login_manager = LoginManager()
login_manager.init_app(app)
Session(app)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({
        'redirect':'login.html'
    })

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.name = username

FLASK_PORT, NGROK_API, NGROK_TOKEN, DATABASE, USER, PASSWORD, HOST, PORT, TABLE, USERS = rotom.enviromentals(
    'FLASK_PORT',
    'NGROK_API',
    'NGROK_TOKEN',
    'POSTGRESQL_DBNAME',
    'POSTGRESQL_USER',
    'POSTGRESQL_PASSWD',
    'POSTGRESQL_HOST',
    'POSTGRESQL_PORT',
    'POSTGRESQL_TABLE_FOR_TASKS',
    'POSTGRESQL_TABLE_FOR_USERS',
    )

def git_commit():
    (REMOTE_NAME,) = rotom.enviromentals("GIT_REMOTE_NAME")
    subprocess.run(["git", "fetch", f"{REMOTE_NAME}"], check=True)
    subprocess.run(["git", "rebase", f"{REMOTE_NAME}/main"], check=True)
    subprocess.run(["git", "add", "docs/env.json"], check=True)
    subprocess.run(["git", "commit", "-m", f"Update env.json {datetime.datetime.now().isoformat()}"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)

def start_ngrok():
    subprocess.run(
        ["ngrok", "config", "add-authtoken", NGROK_TOKEN],
        capture_output=True,
        text=True,
        check=True
    )
    return subprocess.Popen(
        ["ngrok", "http", str(FLASK_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def get_ngrok_url(retries=5):
    for _ in range(retries):
        time.sleep(5)
        try:
            response = requests.get(NGROK_API).json()
            for tunnel in response["tunnels"]:
                if tunnel["proto"] == "https":
                    return tunnel["public_url"]
        except Exception as e:
            print({e})
    return None

def save_env_url(url, state):
    with open("docs/env.json", "r") as p: prev_env = json.load(p)
    if prev_env.get('url', '') == url: return
    env_data = {"url": url, "state":state}
    with open("docs/env.json", "w") as f:
        json.dump(env_data, f, indent=2)
    git_commit()

def submit_task(details: dict):
    template = ('defect', 'threshold', 'creation', 'status', 'hash', 'market', 'username')
    defect = details.get('defect', ''); price = details.get('threshold', 0)
    details['hash'] = rotom.hash_function(defect, price)
    details['status'] = "submitted"

    if price <= 0 or price >= 500:
        return "Price should lie between 0 and 500", False
    
    config = json.loads(fetch_options().get_data(as_text=True))
    if defect not in config:
        return f"Unable to access configuration for the defect {details['defect']}", False
    else:
        markets = details.get('market', ['eBay'])
        marketplaces = config.get(defect).get('marketplace', [])
        for market in markets:
            if market not in marketplaces:
                return f"The marketplace '{market}' is unavailable", False

    try:
        with open('logs/app.log', 'a') as fp: fp.write(f'{details}\n')
        rotom.postgresql(
            "INSERT INTO tables (columns) VALUES (values)",
            rotom.enviromentals("POSTGRESQL_TABLE_FOR_TASKS"),
            template,
            details
        )
    except Exception as e:
        message = f"The task was unable to be added. Check your task fields and try again.", False
        with open('logs/app.log', 'a') as fp: fp.write(f'{e}\n')
    else:
        message = "Task was submitted successfully", True
    finally:
        return message

def sanitizer(details: dict, updating: bool = False):
    name = details.get('name', 'Pikachu'); mail = details.get("email", ''); discord = details.get('discord', '')
    user = details.get('username', ''); pwd = details.get('password', '')
    
    if not updating and not bool(re.fullmatch(r"\w{1,15}", user)):
        return False, "Invalid username. Try again."
    if not updating and len(pwd) < 8:
        return False, "Password must be at least 8 characters."
    if not updating and not re.search(r"[A-Z]", pwd):
        return False, "Include at least one uppercase letter."
    if not updating and not re.search(r"[a-z]", pwd):
        return False, "Include at least one lowercase letter."
    if not updating and not re.search(r"\d", pwd):
        return False, "Include at least one digit."
    if not updating and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
        return False, "Include at least one special character."
    if not updating and pwd.strip() != pwd:
        return False, "No leading or trailing whitespace."
    if mail and not bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", mail)):
        return False, "Invalid Email. Try again."
    if discord and not (bool(re.match(r"^[\w]{2,32}#\d{4}$", discord)) or bool(re.match(r"^[a-z0-9_.]{2,32}$", discord))):
        return False, "Invalid Discord. Try again."
    if name and not bool(re.fullmatch(r"[ \w.'@-]{1,32}", name.strip())):
        return False, "Invalid display name. Try again."
    return True, ""

def main():
    print("🔁 Starting Flask and Ngrok...")

    ngrok_proc = start_ngrok()

    print("⏳ Waiting for Ngrok tunnel...")
    public_url = get_ngrok_url()

    if public_url:
        print(f"🌐 Ngrok URL: {public_url}")
        save_env_url(public_url, "active")
        print("✅ Saved env.json")
    else:
        print("❌ Failed to retrieve Ngrok URL")

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    try:
        app.run(port=FLASK_PORT)
    except Exception as e:
        print(f"\n Something went wrong {e}")

    print("\n🛑 Shutting down...")
    save_env_url(public_url, "expired")
    ngrok_proc.terminate()

@app.route("/")
def ping():
    return "<p>OK</p>"

@app.route("/options")
@login_required
def fetch_options():
        response = {}
        with open("config.json") as config:
            options = json.load(config)
        for key, val in options.items():
            response[key] = {
                "title": val["title"],
                "marketplace": val["marketplace"]
        }
        return jsonify(response)

@app.route("/login", methods=["POST"])
def login():
    success = False; message = ""
    try:
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        remembrance = request.form.get("remember-me", "") == "on"

        results = rotom.postgresql(
            'SELECT columns FROM credentials WHERE username = %s',
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_USERS'),
            ('username', 'password'),
            {'username': username},
            1
        )

        if results:
            result = results.pop()
            if result and bcrypt.checkpw(password.encode(), str(result['password']).encode()):
                user = User(username)
                if remembrance: session.permanent = True
                login_user(user)
                success, message = True, ""
            else:
                message = "The credentials are incorrect"
        else:
            message = "We do not have your records"

    except Exception as e:
        message = str(e)

    finally:
        return jsonify({
            "success": success,
            "message": message
        })
    
@app.route("/register", methods=["POST"])
def register():
    success = False; message = ""
    try:
        credentials = {
            'name': 'Pikachu',
            'username': request.form.get("username", ""),
            'password': request.form.get("password", ""),
            'email': request.form.get("email", ""),
            'discord': request.form.get("discord", "")
        }

        goodOrBad, message = sanitizer(credentials)

        if not goodOrBad:
            return jsonify({"success": False, "message": message})
        
        message = f"{' '.join(credentials.values())}"

        salt = bcrypt.gensalt()
        credentials['password'] = (bcrypt.hashpw((credentials['password']).encode(), salt)).decode()

        rotom.postgresql(
            "INSERT INTO tables (columns) VALUES (values)",
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_USERS'),
            ("username", "password", "email", "discord", "name"),
            credentials
        )
    
    except Exception as e:
        message = str(e)

    else:
        success, message = True, "You've been registered successfully"
    
    finally:
        return jsonify({
            "success": success,
            "message": message
        })

@app.route("/submit", methods=["POST"])
@login_required
def submit():
    message = ""; success = False
    try:
        message, success = submit_task({
            "defect": request.form.get("defect", "wartortle_evolution_error"),
            "threshold": float(request.form.get("price", 0)),
            "creation": datetime.datetime.now(datetime.timezone.utc),
            "market": [request.form.get("marketplace", "eBay")],
            "username": current_user.id
        })

    except Exception as e:
        success = False
        message = str(e)
    
    finally:
        return jsonify({
            "success": success,
            "message": message
        })

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    session.modified = True
    return jsonify({'redirect':'login.html'})

@app.route('/user-info')
@login_required
def send_info():
    username = current_user.id

    data = rotom.postgresql(
        f"SELECT tables FROM columns WHERE username = '{username}'",
        rotom.enviromentals('POSTGRESQL_TABLE_FOR_USERS'),
        ('name', 'email', 'discord'),
        limit=1
    )

    user_data = data.pop() if data else {}

    info_data = rotom.postgresql(
        f"SELECT columns FROM tables WHERE username = '{username}'",
        rotom.enviromentals("POSTGRESQL_TABLE_FOR_TASKS"),
        ('defect', 'threshold', 'creation', 'status', 'market')
    )

    return jsonify({
        "data": user_data,
        "info": info_data
    })

@app.route('/update', methods=['POST'])
@login_required
def update_info():
    success, message = False, ""
    try:
        details = {
            'name': request.form.get("name", ""),
            'email': request.form.get("email", ""),
            'discord': request.form.get("discord", "")
        }
        goodOrBad, message = sanitizer(details, True)
        if not goodOrBad:
            return jsonify({
                "success": False,
                "message": message
            })
        
        rotom.postgresql(
            f"UPDATE tables SET columns WHERE username = '{current_user.id}'",
            rotom.enviromentals('POSTGRESQL_TABLE_FOR_USERS'),
            tuple([key+' = %s' for key in ("name", "email", "discord")]),
            details
        )
 
    except Exception as e:
        message = str(e)

    else:
        success = True
    
    finally:
        return jsonify({
            "success": success,
            "message": message
        })

if __name__ == "__main__":
    main()