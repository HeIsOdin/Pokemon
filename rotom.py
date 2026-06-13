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

from argparse import ArgumentParser, Namespace
from dotenv import load_dotenv
from datetime import datetime
from cv2.typing import MatLike as MAT # type hinting, no import

import os
import sys
import json
import psycopg2
import cv2
import numpy as np
import shutil
import logging
import re
import subprocess
import hashlib

def env(vars: str, defaults: str = '', delimiter: str = ",") -> tuple[str, ...]:
    """
    Retrieve environment variables.

    Args:
        vars      (str): variables set in the environment
        defaults  (str): default values for the variables, separated by the specified delimiter
        delimiter (str): the character used to separate default values in the defaults string
    
    Returns:
        tuple (number of arguments passed): values of environmental variables
    """
    values: list[str] = []
    l_vars = vars.split(delimiter); l_defaults = defaults.split(delimiter)
    while len(l_defaults) < len(l_vars): l_defaults.append('') # Pad defaults with empty strings if not enough provided
    for var, default in zip(l_vars, l_defaults):
        value = os.getenv(var.strip())
        if value: values.append(value)
        else: values.append(default.strip())
    
    if len(values) != len(l_vars):
        raise Exception(f"Some or all values in {vars} not set in environment without defaults.")

    return tuple(values)

def module_arguments(desc: str, subcommands: dict[str, dict] | None = None) -> Namespace:
    """
    Parse command-line arguments for the main script.
    Args:
        - desc (str) : Description of the main script for help text.
        - subcommands (dict) : A dictionary with keys as subcommand names and values are dicts
    Returns:
        argparse.Namespace: Parsed argument object.
    """
    if not subcommands: raise ValueError("Subcommands dictionary must be provided.")
    parser = ArgumentParser(description=desc)
    subparsers = parser.add_subparsers(dest='command', required=True)
    for cmd, args in subcommands.items():
        subparser = subparsers.add_parser(cmd, description=args.get('desc', ''))
        for arg, params in args.get('args', {}).items(): subparser.add_argument(arg, **params)
    return parser.parse_args()

def postgresql(sql: str, table: tuple, template : tuple[str, ...] = (), pairs: dict | None = None, limit: int = -1,):
    HOST, PORT = env('POSTGRESQL_HOST,POSTGRESQL_PORT', 'localhost,5432')
    DATABASE, USER, PASSWORD = env('POSTGRESQL_DBNAME,POSTGRESQL_USER,POSTGRESQL_PASSWD')
    
    with psycopg2.connect(database=DATABASE, user=USER, password=PASSWORD, host=HOST, port=PORT) as conn:
        with conn.cursor() as cursor:

            keyword = sql.split()[0].upper()
            if pairs is None: pairs = {}

            table_names = ', '.join(table); sql = sql.replace('{{tables}}', table_names)
            filters = ' AND '.join([k+' = %s' for k in pairs.keys() if k not in template]); sql = sql.replace('{{filters}}', filters)
            data = tuple(pairs.values())

            columns = ', '.join(template); sql = sql.replace('{{columns}}', columns)
            values = ', '.join(['%s' for _ in template]); sql = sql.replace('{{values}}', values)
            cols_and_vals = ', '.join([f"{k} = %s" for k in template]); sql = sql.replace('{{cols_and_vals}}', cols_and_vals)
            
            if keyword == "UPDATE" or keyword == "INSERT" or keyword == "DELETE":
                cursor.execute(sql, data)
                conn.commit()
                return []
            
            if keyword == "SELECT":
                cursor.execute(sql, data)
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

            else: raise ValueError("Only SELECT, UPDATE, INSERT, DELETE are allowed.")

def show_image(img: MAT|bytes, NAME: str, title: str = '') -> bool | None:
    """
    Display an image in a window with error handling.

    Args:
        - img (MatLike): Image matrix to display.
    Returns:
        bool: True if user accepted the image (Enter), False if rejected (Escape) or on error.
    """
    if isinstance(img, bytes):
        img_array = np.frombuffer(img, dtype=np.uint8)
        img_decode = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img_decode is not None:
            image = img_decode
        else:
            return None
    elif isinstance(img, np.ndarray):
        image = img
    else:
        return None
    if not title: title = NAME
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)

    cv2.resizeWindow(title, 1400, 1000)
    cv2.moveWindow(title, 50, 50)

    cv2.imshow(title, image)
    ch = cv2.waitKey(0)
    # Enter: 13, Escape: 27, Backspace: 8
    if ch == 27: raise SystemExit("User requested exit.")
    if ch == 8: return False
    if ch == 13: return True
    if title != NAME: cv2.destroyWindow(title)
    return None

def sanitize_filename(raw_name: str, max_len: int = 35) -> str:
    """
    Sanitize a raw string into a filesystem-safe filename.
    Replaces all non-alphanumeric characters (except ., _, -) with underscores,
    collapses consecutive underscores, and enforces a maximum length.
    Args:
    - raw_name (str): The original string to sanitize.
    - max_len (int): Maximum length of the sanitized filename (excluding extension).
    Returns:
    - str: A sanitized filename with the same extension as the original.
    """
    stem, ext = os.path.splitext(raw_name)
    clean = re.compile(r'[^a-zA-Z0-9._-]').sub('_', stem)[:max_len]
    clean = re.sub(r'_+', '_', clean).strip('_')
    return f"{clean or 'unnamed'}{ext}"

def configure_logger(name: str, debug: bool = False) -> None:
    """
    Configure a logger for the given name.
    If debug is True, logs will be printed to the console.
    Otherwise, logs will be written to a file in the 'logs' directory.
    Args:
        - name (str): The name of the logger (e.g., the module or class name).
        - debug (bool): logs will be printed to the console if true otherwise to a file.
    """
    logger = logging.getLogger(name.title())
    os.makedirs('logs', exist_ok=True)
    if logger.handlers: return  # Avoid adding multiple handlers if logger is already configured
    if debug:
        load_dotenv() # docker-compose will set env vars, so no need to load them in production
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
    else:
        logger.setLevel(logging.WARNING)
        LOG_DIR = env('LOG_DIR', 'logs')[0]
        LOG_FILE = f'{LOG_DIR}/{name}.log'
        open(LOG_FILE, 'w').close()  # Ensure log file exists
        handler = logging.FileHandler(f'logs/{name}.log')
    formatter = logging.Formatter('[%(name)s] %(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def save_image(img: MAT|bytes, path: str, suffix: str = "", sep: str = "_") -> None:
    """
    Save an image to disk with error handling.

    Args:
        - img (MatLike or bytes): Image data to save
        - path (str): Desired file path to save the image.
        - suffix (str): Optional suffix to append to the filename before the extension.
    """
    dir = os.path.dirname(path)
    os.makedirs(dir, exist_ok=True)
    filename = os.path.basename(path)
    _, ext = os.path.splitext(filename)
    name = hashlib.md5(img).hexdigest()[:8]
    filename = f"{name}{sep if suffix else ''}{suffix}{ext}"
    path = os.path.join(dir, filename)
    if isinstance(img, np.ndarray): cv2.imwrite(path, img)
    elif isinstance(img, (bytes, bytearray)):
        with open(path, 'wb') as f: f.write(img)

def push_dataset_to_kaggle(dataset_dir: str, message: str = '') -> subprocess.CompletedProcess:
    """
    This function pushes the dataset to Kaggle using the Kaggle API.
    It assumes that the Kaggle API is configured and authenticated properly.
    """
    # check if kaggle CLI is available
    if shutil.which("kaggle") is None: raise Exception("Please install the Kaggle API")

    # check if kaggle.json exists
    kaggle_json = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
    if not os.path.isfile(kaggle_json): raise Exception(f"No Kaggle API key at {kaggle_json}")
    
    # check if dataset_metadata.json exists (created by kaggle CLI on first push)
    metadata_path = os.path.join(dataset_dir, "dataset-metadata.json")
    if not os.path.isfile(metadata_path):
        raise Exception(f"Missing Kaggle dataset metadata. Initialize or download the dataset")

    # push to Kaggle
    if not message: message = f"Updated dataset at {datetime.now().isoformat()}"
    args = ["kaggle", "datasets", "version", "-p", dataset_dir, "-m", message, "-r", "zip"]
    return subprocess.run(args, cwd=dataset_dir)

def load_config(config: str| dict = 'config.json') -> dict:
    """
    Load a JSON configuration file and return it as a dictionary.
    Args:
        - config (str or dict): Path to the JSON configuration file or a preloaded dictionary.
    Returns:
        dict: The loaded configuration as a dictionary.
    """
    if isinstance(config, dict) and len(config.keys()) > 0: return config
    if not isinstance(config, str) or not config.strip():
        raise ValueError("Config must be a file path or a non-empty dictionary.")
    config_path = config
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        try:
            cfg = json.load(f)
            return cfg
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON configuration: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error loading configuration: {e}")