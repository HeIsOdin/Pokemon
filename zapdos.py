"""
(remake)
# Zapdos
> Behold, the elegant Zapdos, the face of PyPikachu!  

This is a Flask-based web application that serves as the backend for PyPikachu. The application handles user authentication.

## Routes
- `GET    /`       : Collection of listings the system is trained to detect.
- `GET    /health` : Provides a health check for the application.
- `GET    /token`  : Provides token to use to connect to Discord bot.
- `POST   /token` : Revokes the token to disconnect from Discord bot. (To be refactored)
- `POST   /login`  : Authenticates users and establishes a session.
- `POST   /me`     : Registers new users with the system.
- `PATCH  /me`     : Allows users to reset their creds or delete their account. (To be refactored)
- `DELETE /me`     : Deletes the user's account. (To be refactored)
"""

import dis

from flask import Flask, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_session import Session
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv

import os
import sys
import rotom
import bcrypt
import logging
import requests
import secrets

app = Flask(__name__)
CORS(app, supports_credentials=True,
    origins=list(rotom.env('CORS_ORIGIN', 'http://localhost:3000')))
(app.secret_key,) = rotom.env('FLASK_SECRET_KEY')

app.config['SESSION_TYPE'] = 'filesystem'
SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_sessions')
if not os.path.exists(SESSION_FILE_DIR): os.makedirs(SESSION_FILE_DIR)
app.config['SESSION_FILE_DIR'] = SESSION_FILE_DIR
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True
)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=100)

login_manager = LoginManager()
login_manager.init_app(app)
Session(app)

TOKENS = {}

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

def __logoutHelper__():
    logout_user()
    session.clear()
    session.modified = True

def __logout_helper_response__():
    __logoutHelper__()
    return {'redirect':'login.html'}

def __hashPassword__(password: str) -> str:
    salt = bcrypt.gensalt()
    return (bcrypt.hashpw(password.encode(), salt)).decode()

def __getValidCredentials__() -> dict[str, str]:
    url = rotom.env('USERNAME_GENERATOR_URL')[0]
    req = requests.get(url)
    req.raise_for_status()
    data: dict = req.json()
    results = data.get('results', [])
    result = results[0] if results else {}
    credentials: dict[str, str] = result.get('login', {})
    
    if not credentials:
        app.logger.error(f"[Username Generation]: Received response {req.text} from {url}")
        app.logger.error(f"[Username Generation]: Received username '{credentials}' from {data}")
        raise ValueError("Failed to generate username. Please try again.")
    return credentials

def __login_helper__(username: str, password: str, remembrance: bool = False):
    resp = {}
    try:
        app.logger.info(f"[Login Info]: user={username}, passwd={password}, rem={remembrance}")

        records = rotom.postgresql(
            'SELECT {{columns}} FROM {{tables}} WHERE {{filters}}',
            rotom.env('POSTGRESQL_TABLE_FOR_USERS'),
            ('password',),
            {'username': username},
            1
        )
        if not records: raise ValueError("The credentials are incorrect.")

        record: dict[str, str] = records[0]
        actual_password = record.get('password', '')
        if not actual_password: raise ValueError("The credentials are incorrect.")
        if bcrypt.checkpw(password.encode(), actual_password.encode()):
            user = User(username)
            if remembrance: session.permanent = True
            login_user(user)
            resp = {'redirect':'dashboard.html', 'success': True}
        else: raise ValueError("The credentials are incorrect.")

    except ValueError as ve:
        app.logger.debug(f"[Login Debug]: {ve}")
        resp = {'message': str(ve), 'success': False}

    except Exception as e:
        app.logger.exception(f"[Login Error]: {e}")
        resp = {'message': "An error occurred during login. Please try again.", 'success': False}

    return resp

def __register_helper__(username: str, password: str):
    resp = {}
    try:
        if not username: raise ValueError("Failed to generate username. Please try again.")
        credentials = {
            'username': username,
            'password': password,
        }

        credentials['password'] = __hashPassword__(credentials['password'])

        rotom.postgresql(
            "INSERT INTO {{tables}} ({{columns}}) VALUES ({{values}})",
            rotom.env('POSTGRESQL_TABLE_FOR_USERS'),
            ("username", "password",),
            credentials
        )
        resp = {'message':"Registration successful!", 'redirect':'login.html', 'success':True, 'username': username}

    # # catch unique violation error for username and return a user-friendly message
    # except rotom.psycopg2.errors.UniqueViolation:
    #     app.logger.debug(f"[Registration Debug]: Username '{username}' already exists.")
    #     resp = {'message': "Username already exists. Please try again.", 'success': False}

    except ValueError as ve:
        app.logger.debug(f"[Registration Debug]: {ve}")
        resp = {'message':str(ve), 'success':False}

    except Exception as e:
        app.logger.exception(f"[Registration Error]: {e}")
        resp = {'message':"An error occurred. Please try again", 'success':False}

    return resp

def __update_info_helper__(username: str, details: dict):
    resp = {}
    try:
        reg_password = details.get('password', '')
        if not reg_password: details.pop('password', None)
        else: details['password'] = __hashPassword__(reg_password)

        rotom.postgresql(
            "UPDATE {{tables}} SET {{cols_and_vals}} WHERE {{filters}}",
            rotom.env('POSTGRESQL_TABLE_FOR_USERS'),
            tuple(details.keys()),
            {**details, 'username': username}
        )
        __logoutHelper__()
        resp = {'message':"Update successful!", 'redirect':'login.html', 'success':True}

    except ValueError as ve:
        app.logger.debug(f"[Update Debug]: {ve}")
        resp = {'message':str(ve), 'success':False}

    except Exception as e:
        app.logger.exception(f"[Update Error]: {e}")
        resp = {'message':"An error occurred. Please try again", 'success':False}

    return resp

def __delete_account_helper__(username: str):
    resp = {}
    try:
        rotom.postgresql(
            "DELETE FROM {{tables}} WHERE {{filters}}",
            rotom.env('POSTGRESQL_TABLE_FOR_USERS'),
            (),
            {'username': username}
        )
        __logoutHelper__()
        resp = {'message':"Account deleted successfully.", 'redirect':'login.html', 'success':True}
    except Exception as e:
        app.logger.exception(f"[Account Deletion Error]: {e}")
        resp = {'message':"An error occurred. Please try again.", 'success':False}
    return resp

def __get_token_helper__(username: str):
    resp = {}
    try:
        token = secrets.token_urlsafe(32)
        app.logger.info(f"[Generating Token]: {token} for user {username}")
        TOKENS[username] = (token, datetime.now() + timedelta(minutes=5))
        resp = {'token': token, 'success': True}
    except Exception as e:
        app.logger.exception(f"[Token Generation Error]: {e}")
        resp = {'message': "An error occurred. Please try again.", 'success': False}
    return resp

def __revoke_token_helper__(username: str, token: str, discord_id: str):
    resp = {}
    try:
        if not token: raise ValueError("Token is required.")
        app.logger.info(f"[Revoking Token]: {token} for user {username}")
        if not any(token == t[0] and t[1] > datetime.now() and i == username
                   for i, t in TOKENS.items()): raise ValueError("Invalid or expired token.")
        TOKENS.pop(username, None)
        rotom.postgresql(
            "UPDATE {{tables}} SET {{cols_and_vals}} WHERE {{filters}}",
            rotom.env('POSTGRESQL_TABLE_FOR_USERS'),
            ("discord",),
            {'discord': discord_id, 'username': username}
        )
        resp = {'message': "Token revoked successfully.", 'success': True}
    except Exception as e:
        app.logger.exception(f"[Token Revocation Error]: {e}")
        resp = {'message': "An error occurred. Please try again.", 'success': False}
    return resp

@app.get("/")
def home():
    resp = {}
    try:
        records = rotom.postgresql(
            'SELECT {{columns}} FROM {{tables}}',
            rotom.env('POSTGRESQL_TABLE_FOR_LISTINGS'),
            ('id', 'url', 'image', 'misprint', 'certainty')
        )
        if not records: raise ValueError("No listings found.")
    
    except ValueError as ve:
        app.logger.debug(f"[Listing Debug]: {ve}")
        return jsonify({'message': str(ve), 'success': False})
    
    except Exception as e:
        app.logger.exception(f"[Listing Error]: {e}")
        return jsonify({'message': "An error occurred. Please try again later.", 'success': False})
    finally: return jsonify(resp)

@app.route("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    remembrance = request.form.get("remember-me", "") == "on"
    resp = __login_helper__(username, password, remembrance)
    return jsonify(resp)
    
@app.post("/me")
def register():
    username = __getValidCredentials__().get('username', '')
    password = request.form.get("password", "")
    resp = __register_helper__(username, password)
    return jsonify(resp)

@app.post('/me')
@login_required
def update_info():
    details = {
        'password': request.form.get("password", ""),
    }
    resp = __update_info_helper__(current_user.id, details)
    return jsonify(resp)

@app.delete('/me')
@login_required
def delete_account():
    resp = __delete_account_helper__(current_user.id)
    return jsonify(resp)
    
@app.get('/token')
@login_required
def get_token():
    resp = __get_token_helper__(current_user.id)
    return jsonify(resp)

@app.post('/token')
def revoke_token():
    req: dict[str, str] = request.get_json()
    token = req.get('token', '')
    discord_id = req.get('discord_id', '')
    resp = __revoke_token_helper__(current_user.id, token, discord_id)
    return jsonify(resp)

@app.route('/logout')
@login_required
def logout():
    app.logger.info(f"[User Logout]: {current_user.id}")
    resp = __logout_helper_response__()
    return jsonify(resp)

@app.route("/health")
def ping():
    checklist = []
    checks = []
    username = reg_password = token_for_revocation = ''
    discord_id = '1234567890123456789'

    checklist.append('PyPikachu is reachable.')
    checks.append(True)
    app.logger.info(f"PyPikachu is reachable. { 'Success' if checks[-1] else 'Failure' }")

    checklist.append('Database connection is healthy.')
    try:
        rotom.postgresql('SELECT 1', rotom.env('POSTGRESQL_TABLE_FOR_USERS'))
        checks.append(True)
    except Exception as e:
        app.logger.exception(f"[Database Connection Error]: {e}")
        checks.append(False)
    app.logger.info(f"Database connection is healthy. { 'Success' if checks[-1] else 'Failure' }")
    
    checklist.append('User registration is functional.')
    try:
        credentials = __getValidCredentials__()
        username = credentials.get('username', '')
        reg_password = credentials.get('password', '')
        resp: dict[str, str | bool] = __register_helper__(username, reg_password)
        username = str(resp.get('username', '') if resp.get('success') else '')
        if resp.get('success'): checks.append(True)
        else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Registration Error]: {e}")
        username = ''
        checks.append(False)
    app.logger.info(f"User registration is functional. { 'Success' if checks[-1] else 'Failure' }")
    
    checklist.append('User login is functional.')
    try:
        if not username:
            checks.append(False)
        else:
            resp = __login_helper__(username, reg_password, False)
            if resp.get('success'): checks.append(True)
            else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Login Error]: {e}")
        checks.append(False)
    app.logger.info(f"User login is functional. { 'Success' if checks[-1] else 'Failure' }")

    checklist.append('User info update is functional.')
    try:
        if not username:
            checks.append(False)
        else:
            new_password = __getValidCredentials__().get('password', '')
            resp_1: dict[str, str | bool] = __update_info_helper__(username, {'password': new_password})
            resp_2: dict[str, str | bool] = __login_helper__(username, new_password, False)
            resp_1_success = resp_1.get('success', False)
            resp_2_success = resp_2.get('success', False)
            resp = {'success': resp_1_success and resp_2_success}
            if resp.get('success'): checks.append(True)
            else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Info Update Error]: {e}")
        checks.append(False)
    app.logger.info(f"User info update is functional. { 'Success' if checks[-1] else 'Failure' }")

    checklist.append('Token generation is functional.')
    try:
        if not username:
            checks.append(False)
        else:
            resp = __get_token_helper__(username)
            if resp.get('success') and resp.get('token'):
                token_for_revocation = str(resp.get('token', ''))
                checks.append(True)
            else:
                token_for_revocation = ''
                checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Token Generation Error]: {e}")
        token_for_revocation = ''
        checks.append(False)
    app.logger.info(f"Token generation is functional. { 'Success' if checks[-1] else 'Failure' }")

    checklist.append('Token revocation is functional.')
    try:
        if not username or not token_for_revocation:
            checks.append(False)
        else:
            resp = __revoke_token_helper__(username, token_for_revocation, discord_id)
            if resp.get('success'): checks.append(True)
            else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Token Revocation Error]: {e}")
        checks.append(False)
    app.logger.info(f"Token revocation is functional. { 'Success' if checks[-1] else 'Failure' }")
    
    checklist.append('User logout is functional.')
    try:
        resp = {k:str(v) for k,v in __logout_helper_response__().items()}
        if resp.get('redirect') == 'login.html': checks.append(True)
        else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[Logout Error]: {e}")
        checks.append(False)
    app.logger.info(f"User logout is functional. { 'Success' if checks[-1] else 'Failure' }")
    
    checklist.append('User deletion is functional.')
    try:
        if not username:
            checks.append(False)
        else:
            resp = __delete_account_helper__(username)
            if resp.get('success'): checks.append(True)
            else: checks.append(False)
    except Exception as e:
        app.logger.exception(f"[User Deletion Error]: {e}")
        checks.append(False)
    app.logger.info(f"User deletion is functional. { 'Success' if checks[-1] else 'Failure' }")
    
    if len(checklist) != len(checks):
        app.logger.exception(f"[Health Check Error]: Checklist and checks length mismatch.")
        return jsonify({'message': "An error occurred.", 'success': False})
    return jsonify({'checklist': checklist, 'checks': checks, 'success': all(checks)})

def main():
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    log = logging.getLogger('werkzeug')
    if debug:
        log.setLevel(logging.INFO)
        open('logs/zapdos.log', 'w').close()  # Ensure log file exists
        handler = logging.FileHandler('logs/zapdos.log')
        HOST = '127.0.0.1'
        PORT = 5000
    else:
        load_dotenv()
        log.setLevel(logging.ERROR)
        handler = logging.StreamHandler(sys.stdout)
        HOST = '0.0.0.0'
        PORT = int(rotom.env('PORT')[0])
        # docker prefers logs to be sent to stdout

    formatter = logging.Formatter('[Zapdos] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)

    print("Starting Zapdos...")
    try:
        app.run(host=HOST, port=PORT, debug=debug)
    except Exception as e:
        app.logger.exception(f"[Server Error]: {e}")

if __name__ == "__main__":
    main()