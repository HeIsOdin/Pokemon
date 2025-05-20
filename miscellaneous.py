import threading
import os
import time

def make_a_choice(prompt, default_value, timeout=30):
    user_input = [default_value, False]  # Store in list for mutability

    def ask():
        user_input[0] = input(prompt) or default_value
    
    thread = threading.Thread(target=ask)
    thread.start()
    thread.join(timeout)

    if 'Y/n' in prompt:
        try:
            user_input[1] = str(user_input[0]).lower().startswith('y')
        except:
            user_input[1] = False
    return user_input

def clear_terminal():
    # CLear Terminal
    os.system('cls' if os.name == 'nt' else 'clear')

def credentials() -> tuple[str, str]:
    # Load credentials from environment variables
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\033[31m[ERROR] CLIENT_ID or CLIENT_SECRET not set in environment.\033[0m")
        exit()
    return CLIENT_ID, CLIENT_SECRET

def pause(seconds: float):
    time.sleep(seconds)