"""
# Miscellaneous
Utility functions for the PokéPrint Inspector system.

This module provides helper functions used across the project, including:
- Colored terminal logging and message formatting
- Directory and file validation (including dataset extraction)
- Environment variable loading for external credentials
- Argument parsing for main execution scripts
- JSON configuration parsing to pass structured arguments

These utilities are designed to support the main PokéPrint pipeline,
which involves crawling card listings, processing images, and running machine learning models.

Dependencies:
- Standard Python libraries only (os, time, zipfile, json, argparse)

Note:
This module is intended to be imported by other scripts and should not
be run as a standalone executable.
"""


import os
import time
import zipfile
import json
import argparse

def print_with_color(string: str, mode: int, quit: bool = True) -> None:
    """
    Print a colored message to the terminal.
    
    Args:
        - string (str): The message to display.
        - mode (int): 1 = ERROR, 2 = SUCCESS, 3 = WARNING, 4 = INFO.
        - quit (bool): If True, exits the program on ERROR.
    """
    def helper(mode: int) -> str:
        if mode == 1: return 'ERROR'
        elif mode == 2: return 'SUCCESS'
        elif mode == 3: return 'WARNING'
        elif mode == 4: return 'INFO'
        else: return ''
    
    # Print colored output
    print(f"\033[3{str(mode)}m[{helper(mode)}] {string}\033[0m")
    
    # Exit on error if specified
    if mode == 1 and quit:
        exit()

def clear_terminal():
    """
    Clear the terminal screen on Windows or Unix systems.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def credentials() -> tuple[str, str]:
    """
    Retrieve eBay API credentials from environment variables.
    
    Returns:
    - tuple: (CLIENT_ID, CLIENT_SECRET)
    """
    CLIENT_ID = os.getenv('EBAY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET')
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\033[31m[ERROR] CLIENT_ID or CLIENT_SECRET not set in environment.\033[0m")
        exit()
    return CLIENT_ID, CLIENT_SECRET

def pause(seconds: float):
    """Pause the script for a specified number of seconds.

    Args:
        seconds (float): Time to pause in seconds.
    """
    time.sleep(seconds)
    print("")  # Add spacing

def directory_check(data_dir: str) -> bool:
    """
    Check if the directory contains any image files (jpg, png, jpeg).
    
    Args:
        - data_dir (str): The directory path to check.
    
    Returns:
    - bool: True if image files are found, False otherwise.
    """
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
        return len(file_names) > 0

def extract_zipfile(TRAINING_DIR: str) -> str:
    """
    Extract a ZIP file to a directory.
    
    Args:
        - TRAINING_DIR (str): Path to the ZIP file.
    
    Returns:
    - str: Path to the extracted directory.
    """
    zip_file_path = TRAINING_DIR
    extract_to = TRAINING_DIR.replace(".zip", "")
    print_with_color(f"Extracting compressed dataset to {extract_to}...", 4)
    try:
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
    except Exception as e:
        print_with_color(f"Unable to extract compressed dataset: {str(e)}", 1)
    else:
        print_with_color("Dataset Extracted Successfully.", 2)
    return extract_to

def parse_JSON_as_arguments(file: str, defect: str, arg_template: list) -> list:
    """
    Parse a JSON configuration file and extract arguments for a given defect.
    
    Args:
        - file (str): Path to the JSON file.
        - defect (str): The defect key to look up.
        - arg_template (list): List of keys to extract.
    
    Returns:
    - list: List of argument values.
    """
    with open(file, 'r') as fp:
        configs: dict = json.load(fp)[defect]
        print(configs)
    
    args = []
    for key, value in configs.items():
        if key in arg_template:
            if isinstance(value, list):
                args.append(tuple(value))
            elif key == 'dataset':
                author, name = str(value).split("/")
                args.append(author)
                args.append(name)
            else:
                args.append(value)
    return args

def pass_arguments_to_main() -> argparse.Namespace:
    """
    Parse command-line arguments for the main script.
    
    Returns:
    - argparse.Namespace: Parsed argument object.
    """
    parser = argparse.ArgumentParser(description="Train the PokéPrint model")
    parser.add_argument("--defect", type=str, help="Name of the Pokemon Card Defect", required=True)
    parser.add_argument("--use_local_storage", action='store_true', help="Use local image download instead of bytearray")
    parser.add_argument("--use_rgb", action='store_true', help="Use RGB instead of grayscale")
    parser.add_argument("--kaggle_download", action='store_true', help="Download Kaggle dataset")
    return parser.parse_args()
