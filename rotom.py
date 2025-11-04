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
import json
import argparse
import psycopg2
import traceback
import cv2
import zipfile
import time

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

def enviromentals(*vars: str) -> tuple:
    """
    Retrieve environment variables.

    Args:
        - *vars (unknown number of strings): variables set in the environment
    
    Returns:
    - tuple (number of arguments passed): values of environmental variables
    """
    values = []
    for var in vars:
        value = os.getenv(var)
        if value: values.append(value)

    if len(values) != len(vars):
        print(f"\033[31m[ERROR] Some or all values in {vars} not set in environment.\033[0m")
        exit()
    return tuple(values)

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

def parse_JSON_as_arguments(file: str, defect: str, arg_template: list) -> dict:
    """
    Parse a JSON configuration file and extract arguments for a given defect.
    
    Args:
        - file (str): Path to the JSON file.
        - defect (str): The defect key to look up.
        - arg_template (list): List of keys to extract.
    
    Returns:
    - dict: Dictionary containing argument values.
    """
    with open(file, 'r') as fp:
        configs: dict = json.load(fp)[defect]
    
    args = {}
    for key, value in configs.items():
        if key in arg_template:
            if isinstance(value, list):
                args[key] = tuple(value)
            elif key == "dataset":
                if type(value) == str:
                    args['author'], args['dataset'] = value.split("/")
                if type(value) == list: args['author'], args['dataset'] = value
            else:
                args[key] = value
    return args

def pass_arguments_to_main() -> argparse.Namespace:
    """
    Parse command-line arguments for the main script.
    
    Returns:
    - argparse.Namespace: Parsed argument object.
    """
    parser = argparse.ArgumentParser(description="The core of PyPikachu model")
    parser.add_argument("--defect", type=str, help="Name of the Pokemon Card Defect", required=True)
    parser.add_argument("--price", type=float, help="Maximum price you are willing to pay", required=True)
    parser.add_argument("--use_local_storage", action='store_true', help="Use permanent local storage?")
    parser.add_argument("--use_rgb", action='store_true', help="Use RGB instead of grayscale?")
    parser.add_argument("--kaggle_download", action='store_true', help="Download Kaggle dataset")
    parser.add_argument("--verbose", action='store_true', help='Show a verbose output')
    return parser.parse_args()

def hash_function(itemId: str, price: float) -> str:
    encoded_defect = ''.join([str(ord(char)) for char in itemId])
    hash = int(round(price)) * int(encoded_defect)
    return str(hash)

def postgresql(sql: str,  table: tuple, template : tuple[str, ...] = (), pairs: dict = {}, limit: int = -1,):
    DATABASE, USER, PASSWORD, HOST, PORT = enviromentals(
    'POSTGRESQL_DBNAME',
    'POSTGRESQL_USER',
    'POSTGRESQL_PASSWD',
    'POSTGRESQL_HOST',
    'POSTGRESQL_PORT',
    )
    try:
        with psycopg2.connect(database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT) as conn:
            with conn.cursor() as cursor:

                columns = ', '.join(template); sql = sql.replace('columns', columns)
                values = ', '.join(['%s' for _ in template]); sql = sql.replace('values', values)
                table_name = ', '.join(table); sql = sql.replace('tables', table_name)

                data = []
                if pairs:
                    for key in template:
                        key = key.replace(' = %s', '') # Condition when UPDATE is in sql
                        if key in pairs.keys(): data.append(pairs.get(key, None))
                        else:
                            pass

                cursor.execute(sql, tuple(data))
            
                if sql.strip().lower().startswith("select"):
                    results = []
                    rows = cursor.fetchall() if limit == -1 else [cursor.fetchone()] if limit == 1 else cursor.fetchmany(limit)
                    if rows:
                        for row in rows:
                            if row and len(row) == len(template):
                                result = {}
                                for key, value in zip(template, row):
                                    result[key.replace(' = %s', '')] = value
                                results.append(result)
                    return results
                conn.commit()
                return []
    except psycopg2.Error as e:
        os.makedirs('logs', exist_ok=True)
        with open('logs/pidgeotto.log', 'a') as fp:
            fp.write(f'{e}\n{traceback.format_exc()}\n')
        return []  # distinguish error from “no rows”
    except Exception as e:
        os.makedirs('logs', exist_ok=True)
        with open('logs/pidgeotto.log', 'a') as fp:
            fp.write(f'{e}\n{traceback.format_exc()}\n')
        return []

def show_image(image, image_name="demo"):
    cv2.imshow(image_name, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()