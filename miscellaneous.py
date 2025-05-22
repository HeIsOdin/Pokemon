import threading
import os
import time
import zipfile

def print_with_color(string: str, mode: int, quit: bool = True) -> None:
    def helper(mode: int) -> str:
        if mode == 1: return 'ERROR'
        elif mode == 2: return 'SUCCESS'
        elif mode == 3: return 'WARNING'
        elif mode == 4: return 'INFO'
        else: return ''
    print(f"\033[3{str(mode)}m[{helper(mode)}] {string}\033[0m")
    if mode == 1 and quit: exit()


def make_a_choice(prompt: str, default_value: str, timeout: int=30) -> tuple[str, bool]:
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
    return tuple(user_input)

def clear_terminal():
    # CLear Terminal
    os.system('cls' if os.name == 'nt' else 'clear')

def credentials() -> tuple[str, str]:
    # Load credentials from environment variables
    CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\033[31m[ERROR] CLIENT_ID or CLIENT_SECRET not set in environment.\033[0m")
        exit()
    return CLIENT_ID, CLIENT_SECRET

def pause(seconds: float):
    time.sleep(seconds)
    print("")

# ----------------------------------------
# Directory Check
# ----------------------------------------
def directory_check(data_dir: str) -> bool:
    file_names = []
    try:
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith((".jpg", ".png", ".jpeg")):
                    file_names.append(os.path.join(root, file))
    except FileNotFoundError:
        print_with_color(f"No such directory '{data_dir}'", 1, False)
        return False
    else:
        print_with_color(f"Found {len(file_names)} images in {data_dir}", 4)
        return True if len(file_names) > 0 else False
    
def extract_zipfile(dataset_name: str, TRAINING_DIR: str):
    zip_file_path = dataset_name
    extract_to = TRAINING_DIR
    print_with_color(f"Extracting compressed dataset '{dataset_name}' to {TRAINING_DIR}...", 4)
    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
    except Exception as e:
        print_with_color(f"Unable to extract compressed dataset: {str(e)}", 1)
    else:
        print_with_color("Dataset Extracted Successfully.", 2)