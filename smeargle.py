"""
(remake)
# Smeargle
> Behold, the unrelentless artist of the Pokémon world, Smeargle!

This is a utility module for image processing and region of interest (ROI) extraction
It is designed to handle the alignment and cropping of Pokémon card images for defect detection.
It includes functions for loading images, detecting edges and contours.
It is also used in applying perspective transforms, and refining ROIs using template matching.
The module is structured to facilitate debugging by saving intermediate results at each step of the process.
"""

from dotenv import load_dotenv
from rotom import env
from spinarak import main as spinarak_main
from datetime import datetime
from cv2.typing import MatLike as IMG # for type hinting only, not an actual import
from logging import Logger as LOGGER  # for type hinting only, not an actual import

import cv2
import numpy as np
import os
import sys
import logging
import random
import shutil
import yaml
import subprocess

NAME         = 'Smeargle'
ROI_BOX      = (40, 45, 60, 60)  # Example ROI box (x, y, width, height)
CARD_DIM     = (480, 680)  # Target dimensions for aligned card images
INPUT_DIR    = os.path.join('.', 'input')   # Directory for input images
OUTPUT_DIR   = os.path.join('.', 'output')  # Directory for debug outputs
DATASET_DIR  = os.path.join('.', 'dataset') # Directory for final processed dataset
SAMPLE_SIZE  = 50  # Number of images to sample for QA review
SPLIT_RATIO  = (0.8, 0.1, 0.1)  # Train/Val/Test split ratios
ROI_TEMPLATE = os.path.join('roi_templates', 'wartortle_evolution_error.jpg')  # for NCC refinement
DATASET_NAME = "pokemon-tcg-cards"
MAX_FAILURES = 5

MIN_ASPECT_RATIO       = 0.45
MAX_ASPECT_RATIO       = 0.90
MIN_BOX_AREA_RATIO     = 0.20
MAX_BOX_AREA_RATIO     = 0.98
MIN_CONTOUR_AREA_RATIO = 0.10

def _showImage(img: IMG, log: LOGGER) -> bool:
    """
    Display an image in a window with error handling.

    Args:
        - img (MatLike): Image matrix to display.
        - log (Logger): Logger for debug messages.
    """
    title = "Smeargle - Review Detected Contour"
    try:
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)

        cv2.resizeWindow(title, 1400, 1000)
        cv2.moveWindow(title, 50, 50)

        cv2.imshow(title, img)
        ch = cv2.waitKey(0)
        cv2.destroyWindow(title)
        if ch == 27:
            raise SystemExit("User requested exit.")
        if ch != 13:
            return False
    except Exception as e:
        log.error(f"Failed to display image '{title}': {e}")
        return False
    return True

def _saveImage(img: IMG, filename: str, stage: int, log: LOGGER) -> str:
    """
    Save an image to disk with error handling.

    Args:
        - img (MatLike): Image matrix to save.
        - filename (str): Name of the file to save.
        - log (Logger): Logger for debug messages.
    """
    path = os.path.join(OUTPUT_DIR, os.path.splitext(filename)[0])
    if not os.path.isdir(path):
        log.warning(f"Save path '{path}' does not exist. Creating directory.")
        os.makedirs(path, exist_ok=True)
    try:
        if   stage == 1: path = os.path.join(path, "1_original.jpg")
        elif stage == 2: path = os.path.join(path, "2_edges.jpg")
        elif stage == 3: path = os.path.join(path, "3_contours.jpg")
        elif stage == 4: path = os.path.join(path, "4_aligned.jpg")
        elif stage == 5: path = os.path.join(path, "5_roi.jpg")
        cv2.imwrite(path, img)
        log.debug(f"Saved image to {path}")
        return path
    except Exception as e:
        log.error(f"Failed to save image '{path}': {e}")
        return ""

def _saveForYOLO(img: IMG, label: str, filename: str, log: LOGGER) -> str:
    """
    Save a YOLO label to disk with error handling.

    Args:
        - label (str): Label string to save.
        - filename (str): Name of the file to save.
        - log (Logger): Logger for debug messages.
    """
    filename = os.path.splitext(filename)[0]
    path = os.path.join(DATASET_DIR, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        cv2.imwrite(f"{path}.jpg", img)
        if not label: return ""
        with open(f"{path}.txt", "w", encoding="utf-8") as f: f.write(label + "\n")
        return path
    except SystemExit:
        log.info(f"User requested exit. Stopping processing.")
        sys.exit(0)
    except Exception as e:
        log.error(f"Failed to save label '{path}': {e}")
        return ""

def _loadFileFromDirectory(input_dir: str, filepath: str, log: LOGGER) -> IMG | None:
    """
    Load an image from a directory and prepare a save path for debug outputs.

    Args:
        - file (str): Filename of the image.
        - log (Logger): Logger for debug messages.

    Returns:
    - tuple: (image matrix, save path string)
    """

    image_path = os.path.join(input_dir, filepath)

    if not os.path.isfile(image_path):
        log.warning(f"Image file '{image_path}' does not exist.")
        return None

    img = cv2.imread(image_path)
    if img is None:
        log.warning(f"Failed to load image '{image_path}'")
        return None
    return img

def _detectEdges(img: IMG) -> IMG:
    """
    Convert an image to grayscale, apply blur, and detect edges using Canny.

    Args:
        - img (MatLike): Input image matrix.
        - path (str): Directory path to save edge debug image.

    Returns:
    - MatLike: Binary edge map.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    return edges

def _detectContours(img: IMG, edges: IMG, log: LOGGER) -> IMG:
    """
    Detect the largest external contour in an edge image.
    
    Args:
        - img (MatLike): Image to be processed.
        - edges (MatLike): Binary edge map.
        - log (Logger): Logger for debug messages.

    Returns:
    - np.ndarray: Approximated polygon contour points.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Define HSV range for yellow (may need tuning)
    lower_yellow = np.array([20, 80, 80])
    upper_yellow = np.array([40, 255, 255])

    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Morphological cleanup
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.empty((0, 2), dtype=np.int32)

    # Choose the largest yellow region
    border_contour = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(border_contour, True)
    approx = cv2.approxPolyDP(border_contour, 0.02 * peri, True)

    # Use fallback box if not exactly 4 points
    if len(approx) == 4:
        return approx
    fallback_edges = _detectEdges(img)
    contours, _ = cv2.findContours(fallback_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        card_contour = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(card_contour, True)
        for eps in [0.02, 0.015, 0.01, 0.005]:
            approx = cv2.approxPolyDP(card_contour, eps * peri, True)
            if len(approx) == 4:
                return approx
            hull = cv2.convexHull(card_contour)
            approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
            if len(approx) == 4:
                log.warning("[3] Using convex hull fallback")
                return approx
            rect = cv2.minAreaRect(card_contour)
            box = cv2.boxPoints(rect)
            return np.array(box, dtype=np.int32)
    return np.empty((0, 2), dtype=np.int32)

def _contourToYOLO(image: IMG, approx: np.ndarray, log: LOGGER, ratios: dict[str, float]|None = None) -> tuple[IMG|None, str]:
    """
    Convert a 4-point contour into a YOLO axis-aligned bounding-box label.

    Args:
        - image (MatLike): Original image for reference dimensions.
        - approx (np.ndarray): Approximated contour points (should be 4 points).
        - log (Logger): Logger for debug messages.
        - ratios (dict): thresholds for filtering contours based on aspect ratio and area ratios.
    Returns:
        tuple: (image with drawn contours, YOLO label string) or (None, '') if invalid
    """
    if ratios is None: ratios = {}
    min_aspect_ratio       = ratios.get("min_aspect_ratio", MIN_ASPECT_RATIO)
    max_aspect_ratio       = ratios.get("max_aspect_ratio", MAX_ASPECT_RATIO)
    min_box_area_ratio     = ratios.get("min_box_area_ratio", MIN_BOX_AREA_RATIO)
    max_box_area_ratio     = ratios.get("max_box_area_ratio", MAX_BOX_AREA_RATIO)
    min_contour_area_ratio = ratios.get("min_contour_area_ratio", MIN_CONTOUR_AREA_RATIO)
    
    if image is None or getattr(image, "size", 0) == 0:
        log.error("Image is None or empty.")
        return None, ''

    if approx is None or len(approx) != 4:
        log.error(f"Expected 4 points, got {'None' if approx is None else len(approx)}")
        return None, ''

    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        log.error(f"Invalid image dimensions: width={w}, height={h}")
        return None, ''

    pts = approx.reshape(-1, 2).astype(np.float32)

    contour_area = float(cv2.contourArea(pts))
    image_area = float(w * h)
    contour_area_ratio = contour_area / image_area if image_area else 0.0

    x, y, bw, bh = cv2.boundingRect(pts.astype(np.int32))
    box_area = float(bw * bh)
    box_area_ratio = box_area / image_area if image_area else 0.0
    aspect_ratio = (bw / float(bh)) if bh else 0.0

    # Reject tiny contours, nearly full-frame weird boxes, or square-ish icon boxes
    if contour_area_ratio < min_contour_area_ratio:
        log.debug(f"Contour area ratio {contour_area_ratio:.4f} is below threshold")
        return None, ''

    if box_area_ratio < min_box_area_ratio or box_area_ratio > max_box_area_ratio:
        log.debug(f"Box area ratio {box_area_ratio:.4f} is out of range")
        return None, ''

    if not (min_aspect_ratio <= aspect_ratio <= max_aspect_ratio):
        log.debug(f"Aspect ratio {aspect_ratio:.4f} is out of range")
        return None, ''

    x_center = (x + bw / 2.0) / w
    y_center = (y + bh / 2.0) / h
    width = bw / float(w)
    height = bh / float(h)

    cv2.drawContours(image, [pts.astype(np.int32)], -1, (0, 255, 0), 3)
    cv2.rectangle(image, (x, y), (x + bw, y + bh), (255, 0, 0), 2)

    return image, f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"

def _splitDataset(image_files: list[str]):
    """
    This function splits the dataset (train, val, test) based on SPLIT_RATIO.
    It assumes that DATASET_DIR contains all the processed images and labels.
    It moves files into subdirectories for each split.
    """
    # Get all image files
    random.shuffle(image_files)
    
    total = len(image_files)
    train_end = int(total * SPLIT_RATIO[0])
    val_end = train_end + int(total * SPLIT_RATIO[1])

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split, files in splits.items():
        for file in files:
            label_file = os.path.join(DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            shutil.move(os.path.join(DATASET_DIR, file), os.path.join(DATASET_DIR, "images", split, file))
            if os.path.isfile(label_file):
                shutil.move(label_file, os.path.join(DATASET_DIR, "labels", split, os.path.basename(label_file)))

def _createYAML(remote_dataset_path: str):
    """
    This function creates a YAML file for the dataset configuration.
    It assumes that the dataset has been split into train, val, and test directories.
    """
    config = {
        "path": remote_dataset_path,
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {"0": "pokemon_card"}
    }
    yaml_path = os.path.join(DATASET_DIR, "dataset.yaml")
    with open(yaml_path, "w") as f: yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def _pushToKaggle():
    """
    This function pushes the dataset to Kaggle using the Kaggle API.
    It assumes that the Kaggle API is configured and authenticated properly.
    """
    # check if kaggle CLI is available
    if shutil.which("kaggle") is None: raise Exception("Please install the Kaggle API")

    # check if kaggle.json exists
    kaggle_json = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
    if not os.path.isfile(kaggle_json): raise Exception(f"Put your Kaggle API key at {kaggle_json}")

    # check if images, labels, and yaml exist
    if not os.path.isdir(os.path.join(DATASET_DIR, "images")):
        raise Exception("Images directory is missing")
    if not os.path.isdir(os.path.join(DATASET_DIR, "labels")):
        raise Exception("Labels directory is missing")
    if not os.path.isfile(os.path.join(DATASET_DIR, "dataset.yaml")):
        raise Exception("dataset.yaml is missing")
    
    # check if dataset_metadata.json exists (created by kaggle CLI on first push)
    metadata_path = os.path.join(DATASET_DIR, "dataset-metadata.json")
    if not os.path.isfile(metadata_path):
        raise Exception(f"Missing Kaggle dataset metadata. Initialize or download the dataset")

    # push to Kaggle
    message = f"Updated dataset with new cards at {datetime.now().isoformat()}"
    args = ["kaggle", "datasets", "version", "-p", DATASET_DIR, "-m", message, "-r", "zip"]
    subprocess.run(args, check=True)

def push(remote_dataset_path: str = DATASET_DIR):
    """
    This function splits the dataset (train, val, test), creates a YAML file and pushes to Kaggle.
    """
    # load dataset files
    if not os.path.isdir(DATASET_DIR): raise Exception(f"'{DATASET_DIR}' does not exist")
    for m in ("images", "labels"):
        for s in ("train", "val", "test"):
            path = os.path.join(DATASET_DIR, m, s)
            os.makedirs(path, exist_ok=True)
    
    positives = []
    negatives = []
    for file in os.listdir(DATASET_DIR):
        if os.path.splitext(file)[1].lower() in (".jpg", ".jpeg", ".png"):
            label_file = os.path.join(DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            if os.path.isfile(label_file): positives.append(file)
            else: negatives.append(file)
    _splitDataset(positives)
    _splitDataset(negatives)
    
    _createYAML(remote_dataset_path)
    _pushToKaggle()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "progress":
        accepted = rejected = 0
        if not os.path.isdir(DATASET_DIR): raise Exception(f"'{DATASET_DIR}' does not exist")
        files = [f for f in os.listdir(DATASET_DIR)
                if os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")]
        for file in files:
            label_file = os.path.join(DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            if os.path.isfile(label_file): accepted += 1
            else: rejected += 1
        print(f"Progress: {accepted} accepted, {rejected} rejected, {rejected + accepted} total")
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        path = sys.argv[2] if len(sys.argv) > 2 else DATASET_DIR
        return push(path)
    
    qa = len(sys.argv) > 1 and sys.argv[1] == "qa"
    
    debug = len(sys.argv) > 1 and "debug" in sys.argv
    logger = logging.getLogger(NAME)
    os.makedirs('logs', exist_ok=True)
    if debug:
        load_dotenv() # docker-compose will set env vars, so no need to load them in production
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
    else:
        logger.setLevel(logging.WARNING)
        LOG_DIR = env('LOG_DIR', 'logs')[0]
        LOG_FILE = f'{LOG_DIR}/{NAME}.log'
        open(LOG_FILE, 'w').close()  # Ensure log file exists
        handler = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter('[%(name)s] %(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.debug(f"Starting {NAME}...")
    queries = ["pokemon tcg card", "pokemon card vintage", "pokemon card lot", "pokemon card"]
    threshold = float('inf')

    input_dir = DATASET_DIR if qa else INPUT_DIR
    if not os.path.isdir(input_dir) or len([f for f in os.listdir(input_dir)]) < 5:
        logger.warning(f"{input_dir} has too few images. Running Spinarak to populate it...")
        spinarak_main(debug=True, queries=queries, threshold=threshold)

    if not input_dir or not os.path.isdir(input_dir):
        raise Exception(f"Input directory '{input_dir}' does not exist or is not a directory.")

    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and
            os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")]
    if not files: raise Exception(f"No files found in input directory '{input_dir}'")

    image_files = random.sample(files, min(SAMPLE_SIZE, len(files))) if qa else sorted(files)
    if not image_files: raise Exception(f"No image files found in directory '{input_dir}'")

    logger.debug(f"Found {len(image_files)} image files in '{input_dir}'")

    rejects = []
    for file in image_files:
        try:
            # skip if already processed
            save_path = os.path.join(DATASET_DIR, file)
            if os.path.isfile(save_path) and not qa:
                logger.info(f"Skipping '{file}' because it has already been processed.")
                continue

            image = _loadFileFromDirectory(input_dir, file, logger)
            if image is None:
                logger.warning(f"Skipping '{file}' due to load failure.")
                continue

            if debug: _saveImage(image, file, 1, logger)

            image_edges = _detectEdges(image)
            if debug: _saveImage(image_edges, file, 2, logger)

            approx = _detectContours(image, image_edges, logger)

            if len(approx) != 4:
                logger.warning(f"Skipping '{file}' because card corners could not be detected.")
                continue

            yolo_img, label = _contourToYOLO(image.copy(), approx, logger)

            if yolo_img is None:
                logger.warning(f"Skipping '{file}' because YOLO image could not be generated.")
                continue

            choice = _showImage(yolo_img, logger)
            label_exist = os.path.isfile(os.path.splitext(save_path)[0] + ".txt")
            if not choice:
                logger.debug(f"User rejected '{file}'")
                if label_exist:
                    rejects.append((file, label))
                    _saveImage(yolo_img, file, 3, logger)  # save rejected image for debugging
                label = ''
            else:
                logger.debug(f"User accepted '{file}'")
                if not label_exist:
                    rejects.append((file, label))
                    _saveImage(yolo_img, file, 3, logger)  # save accepted image for debugging

            if not qa: _saveForYOLO(image, label, file, logger)
            elif len(rejects) >= MAX_FAILURES:
                logger.warning("Too many rejections during QA. Stopping process.")
                break

        except Exception as e: logger.warning(f"Failed to process '{file}': {e}")
    logger.debug(f"Processed {len(image_files)} files.")
    if qa:
        print(f"QA results: {len(image_files)-len(rejects)} accepted, {len(rejects)} rejected.")
        print("Rejected files: " + ", ".join(f"{file} (label: '{label}')" for file, label in rejects))

if __name__ == "__main__":
    main()