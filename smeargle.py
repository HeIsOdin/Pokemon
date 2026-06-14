"""
(remake)
# Smeargle
> Behold, the unrelentless artist of the Pokémon world, Smeargle!

This is a utility module for image processing and region of interest (ROI) extraction
It is designed to handle the alignment and cropping of Pokémon card images for defect detection.
It includes functions for loading images, detecting edges and contours.
It is also used in applying perspective transforms, and refining ROIs using template matching.
The module is structured to facilitate debugging by saving intermediate results at each stage.
"""

from rotom import configure_logger, env, show_image, module_arguments, save_image, push_dataset_to_kaggle, load_config
from ultralytics import YOLO
from cv2.typing import MatLike as MAT # for type hinting only, not an actual import

import cv2
import numpy as np
import os
import logging
import random
import shutil
import yaml
import json

_NAME            = 'smeargle'
_KAGGLE_ARTIFACT = os.path.join(env("KAGGLE_ARTIFACT", "kaggle")[0])
_MAX_FALSES      = int(env("MAX_FALSES", "5")[0])
_RUN_DIR         = env("RUN_DIR", 'localization')[0]
_YOLO_DIR        = os.path.join(_KAGGLE_ARTIFACT, env("YOLO_DIR", os.path.join("runs", "detect"))[0])
_MODELS_DIR      = env("MODELS_DIR", 'models')[0]
_INPUT_DIR       = env("INPUT_DIR", os.path.join('.', 'input'))[0]
_OUTPUT_DIR      = env("IMAGE_DEBUG_DIR", os.path.join('.', 'output'))[0]
_DATASET_DIR     = env("SMEARGLE_DATASET_DIR", os.path.join('datasets', 'localization'))[0]
_PREDICTIONS_DIR = env("PREDICTIONS_DIR", 'predictions')[0]

_SAMPLE_SIZE = int(env("SAMPLE_SIZE", "50")[0])
_SPLIT_RATIO = tuple(map(float, env("SPLIT_RATIO", "0.8 0.1 0.1")[0].split())) # train/val/test

_MIN_ASPECT_RATIO       = 0.45
_MAX_ASPECT_RATIO       = 0.90
_MIN_BOX_AREA_RATIO     = 0.20
_MAX_BOX_AREA_RATIO     = 0.98
_MIN_CONTOUR_AREA_RATIO = 0.10

_MODEL_PATH = env("YOLO_MODEL_PATH",
                os.path.join(_YOLO_DIR, _MODELS_DIR, _RUN_DIR, "weights", "best.pt"))[0]

def _saveForYOLO(img: MAT, label: str, filename: str) -> str:
    """
    Save a YOLO label to disk with error handling.

    Args:
        - label (str): Label string to save.
        - filename (str): Name of the file to save.
    Returns:
        str: Path where the image and label were saved, or empty string on failure.
    """
    filename = os.path.splitext(filename)[0]
    path = os.path.join(_DATASET_DIR, filename)
    cv2.imwrite(f"{path}.jpg", img)
    if not label: return ""
    with open(f"{path}.txt", "w", encoding="utf-8") as f: f.write(label + "\n")
    return path

def _loadImagesFromDirectory(directory: str, filepaths: list[str]) -> list[MAT | None]:
    """
    Load an image from a directory and prepare a save path for debug outputs.

    Args:
        - file (str): Filename of the image.

    Returns:
        tuple: (image matrix, save path string)
    """
    logger = logging.getLogger(_NAME)
    images: list[MAT|None] = []
    for filename in filepaths:
        image_path = os.path.join(directory, filename)
        if not os.path.isfile(image_path):
            logger.warning(f"Image file '{image_path}' does not exist.")
            images.append(None)
            continue

        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Failed to load image '{image_path}'")
            images.append(None)
            continue
        images.append(img)
    return images

def _detectEdges(img: MAT) -> MAT:
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

def _detectContours(img: MAT) -> MAT | None:
    """
    Detect the largest external contour in an edge image.
    
    Args:
        - img (MatLike): Image to be processed.

    Returns:
        np.ndarray: Approximated polygon contour points.
    """
    logger = logging.getLogger(_NAME)
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
        return None

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
                logger.warning("[3] Using convex hull fallback")
                return approx
            rect = cv2.minAreaRect(card_contour)
            box = cv2.boxPoints(rect)
            return np.array(box, dtype=np.int32)
    return None

def _contourToYOLO(image: MAT, approx: np.ndarray,
                   ratios: dict[str, float]|None = None) -> tuple[MAT|None, str]:
    """
    Convert a 4-point contour into a YOLO axis-aligned bounding-box label.

    Args:
        - image (MatLike): Original image for reference dimensions.
        - approx (np.ndarray): Approximated contour points (should be 4 points).
        - ratios (dict): thresholds for filtering contours based on aspect ratio and area ratios.
    Returns:
        tuple: (image with drawn contours, YOLO label string) or (None, '') if invalid
    """
    logger = logging.getLogger(_NAME)
    if ratios is None: ratios = {}
    min_aspect_ratio       = ratios.get("min_aspect_ratio", _MIN_ASPECT_RATIO)
    max_aspect_ratio       = ratios.get("max_aspect_ratio", _MAX_ASPECT_RATIO)
    min_box_area_ratio     = ratios.get("min_box_area_ratio", _MIN_BOX_AREA_RATIO)
    max_box_area_ratio     = ratios.get("max_box_area_ratio", _MAX_BOX_AREA_RATIO)
    min_contour_area_ratio = ratios.get("min_contour_area_ratio", _MIN_CONTOUR_AREA_RATIO)
    
    if image is None or getattr(image, "size", 0) == 0:
        logger.error("Image is None or empty.")
        return None, ''

    if approx is None or len(approx) != 4:
        logger.exception(f"Expected 4 points, got {'None' if approx is None else len(approx)}")
        return None, ''

    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        logger.exception(f"Invalid image dimensions: width={w}, height={h}")
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
        logger.debug(f"Contour area ratio {contour_area_ratio:.4f} is below threshold")
        return None, ''

    if box_area_ratio < min_box_area_ratio or box_area_ratio > max_box_area_ratio:
        touches_edges = x <= 2 and y <= 2 and x + bw >= w - 2 and y + bh >= h - 2
        card_like = aspect_ratio >= 0.6 and aspect_ratio <= 0.78
        is_full_frame = touches_edges and box_area_ratio >= 0.98 and card_like
        if not is_full_frame:
            logger.warning(f"Box area ratio {box_area_ratio:.4f} is out of range")
            return None, ''

    if not (min_aspect_ratio <= aspect_ratio <= max_aspect_ratio):
        logger.debug(f"Aspect ratio {aspect_ratio:.4f} is out of range")
        return None, ''

    x_center = (x + bw / 2.0) / w
    y_center = (y + bh / 2.0) / h
    width = bw / float(w)
    height = bh / float(h)

    cv2.drawContours(image, [pts.astype(np.int32)], -1, (0, 255, 0), 3)
    cv2.rectangle(image, (x, y), (x + bw, y + bh), (255, 0, 0), 2)

    return image, f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"

def generate(qa: bool = False, progress: bool = False, debug: bool = False):
    """
    Main function to generate the dataset by processing images in the input directory.
    It detects card contours, applies perspective transforms, and saves YOLO labels.
    If 'qa' is True, it will sample a subset of images for manual review.
    If 'progress' is True, it will show the progress of dataset generation.
    If 'debug' is True, it will save intermediate images for debugging purposes.
    
    Args:
        - qa (bool): If True, sample a subset of images for manual review.
        - progress (bool): If True, show the progress of dataset generation.
        - debug (bool): If True, save intermediate images for debugging purposes.
    """
    debug = debug or qa or progress
    configure_logger(_NAME, debug=debug)
    logger = logging.getLogger(_NAME)
    if progress:
        accepted = rejected = 0
        if not os.path.isdir(_DATASET_DIR): raise Exception(f"'{_DATASET_DIR}' does not exist")
        files = [f for f in os.listdir(_DATASET_DIR)
                if os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")]
        for file in files:
            label_file = os.path.join(_DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            if os.path.isfile(label_file): accepted += 1
            else: rejected += 1
        total = accepted + rejected
        logger.debug(f"Progress: {accepted}/{total} accepted, {rejected}/{total} rejected")
        return
    logger = logging.getLogger(_NAME)

    input_dir = _DATASET_DIR if qa else _INPUT_DIR
    if not os.path.isdir(input_dir) or len([f for f in os.listdir(input_dir)]) < _SAMPLE_SIZE:
        logger.error(f"{input_dir} has too few images. Run Spinarak to populate it...")
        return

    if not input_dir or not os.path.isdir(input_dir):
        raise Exception(f"Input directory '{input_dir}' does not exist or is not a directory.")

    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f)) and
            os.path.splitext(f)[1].lower() in (".jpg", ".jpeg", ".png")]
    if not files: raise Exception(f"No files found in input directory '{input_dir}'")

    image_files = random.sample(files, min(_SAMPLE_SIZE, len(files))) if qa else sorted(files)
    if not image_files: raise Exception(f"No image files found in directory '{input_dir}'")

    logger.debug(f"Found {len(image_files)} image files in '{input_dir}'")

    rejects: list[tuple[str, str]] = []
    images: list[MAT|None] = _loadImagesFromDirectory(input_dir, image_files)
    for file, image in zip(image_files, images):
        try:
            if image is None:
                logger.warning(f"Skipping '{file}' due to load failure.")
                continue

            # skip if already processed
            save_path = os.path.join(_DATASET_DIR, file)
            if os.path.isfile(save_path) and not qa:
                logger.info(f"Skipping '{file}' because it has already been processed.")
                continue

            if debug:
                path = os.path.join(_OUTPUT_DIR, os.path.splitext(file)[0], file)
                save_image(image, path, "original")
                path = os.path.join(_OUTPUT_DIR, os.path.splitext(file)[0], file)
                save_image(_detectEdges(image), path, "edges")

            approx = _detectContours(image)

            if approx is None or len(approx) != 4:
                logger.warning(f"Skipping '{file}' because card corners could not be detected.")
                continue

            yolo_img, label = _contourToYOLO(image.copy(), approx)

            if yolo_img is None:
                logger.warning(f"Skipping '{file}' because YOLO image could not be generated.")
                continue

            choice = show_image(yolo_img, _NAME)
            label_exist = os.path.isfile(os.path.splitext(save_path)[0] + ".txt")
            if not choice:
                logger.debug(f"User rejected '{file}'")
                if qa and label_exist:
                    rejects.append((file, label))
                    path = os.path.join(_OUTPUT_DIR, os.path.splitext(file)[0], file)
                    save_image(yolo_img, path, "rejected")  # save rejected image for debugging
                label = ''
            else:
                logger.debug(f"User accepted '{file}'")
                if qa and not label_exist:
                    rejects.append((file, label))
                    path = os.path.join(_OUTPUT_DIR, os.path.splitext(file)[0], file)
                    save_image(yolo_img, path, "accepted")  # save accepted image for debugging

            if not qa: _saveForYOLO(image, label, file)
            elif len(rejects) >= _MAX_FALSES:
                logger.warning("Too many rejections during QA. Stopping process.")
                break

        except Exception as e: logger.warning(f"Failed to process '{file}': {e}")
    logger.debug(f"Processed {len(image_files)} files.")
    if qa:
        rej = len(rejects)
        acc = len(image_files) - rej
        logger.debug(f"""QA results: {acc} accepted, {rej} rejected.""")
        logger.warning("Rejected files: " + ", ".join(f"{f} (label: '{l}')" for f, l in rejects))


def _splitDataset(image_files: list[str]):
    """
    This function splits the dataset (train, val, test) based on _SPLIT_RATIO.
    It assumes that _DATASET_DIR contains all the processed images and labels.
    It moves files into subdirectories for each split.

    Args:
        - image_files (list[str]): List of image filenames to split.
    """
    # Get all image files
    random.shuffle(image_files)
    total = len(image_files)
    train_end = int(total * _SPLIT_RATIO[0])
    val_end = train_end + int(total * _SPLIT_RATIO[1])

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split, files in splits.items():
        for file in files:
            label_file = os.path.join(_DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            dest = os.path.join(_DATASET_DIR, "images", split, file)
            shutil.move(os.path.join(_DATASET_DIR, file), dest)
            if os.path.isfile(label_file):
                dest = os.path.join(_DATASET_DIR, "labels", split, os.path.basename(label_file))
                shutil.move(label_file, dest)

def _create_yaml_and_json():
    """
    This function creates a YAML file for the dataset configuration.
    It assumes that the dataset has been split into train, val, and test directories.
    """
    paths = {
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {"0": "pokemon_card"},
        "model_dir": _MODELS_DIR,
        "run_dir": _RUN_DIR,
        "predictions_dir": _PREDICTIONS_DIR,
    }
    config = load_config(_NAME)
    yaml_path = os.path.join(_DATASET_DIR, "dataset.yaml")
    json_path = os.path.join(_DATASET_DIR, "dataset.json")
    with open(yaml_path, "w") as f: yaml.dump(paths, f, default_flow_style=False, sort_keys=False)
    with open(json_path, "w") as f: json.dump(config, f, indent=4)

def push(message: str):
    """
    This function splits the dataset (train, val, test), creates a YAML file and pushes to Kaggle.
    Args:
        - remote_dataset_path (str): The path where the dataset will be located on Kaggle.
    """
    logger = logging.getLogger(_NAME)
    # load dataset files
    for m in ("images", "labels"):
        for s in ("train", "val", "test"):
            path = os.path.join(_DATASET_DIR, m, s)
            os.makedirs(path, exist_ok=True)
    
    positives = []
    negatives = []
    for file in os.listdir(_DATASET_DIR):
        if os.path.splitext(file)[1].lower() in (".jpg", ".jpeg", ".png"):
            label_file = os.path.join(_DATASET_DIR, f"{os.path.splitext(file)[0]}.txt")
            if os.path.isfile(label_file): positives.append(file)
            else: negatives.append(file)
    _splitDataset(positives)
    _splitDataset(negatives)
    
    _create_yaml_and_json()
    res = push_dataset_to_kaggle(os.path.abspath(_DATASET_DIR), message)
    if res.returncode == 0:
        logger.debug("Dataset pushed to Kaggle successfully.")
    else:
        logger.error(f"Failed to push dataset to Kaggle: {res.stdout} {res.stderr}")

def load_yolo_model(yolo_model: str | None | YOLO = None) -> YOLO:
    """
    Load the YOLO model with error handling.
    Returns:
        YOLO: Loaded YOLO model instance.
    """
    if isinstance(yolo_model, YOLO): return yolo_model
    
    logger = logging.getLogger(_NAME)
    yolo_model_path = yolo_model if isinstance(yolo_model, str) else _MODEL_PATH
    logger.debug(f"Attempting to load YOLO model from '{yolo_model_path}'")
    if not os.path.isfile(yolo_model_path): raise SystemExit(f"'{yolo_model_path}' is invalid")
    
    logger.debug(f"Loaded YOLO model from '{yolo_model_path}'")
    return YOLO(yolo_model_path)

def _extractCrop(img: MAT, bbox: tuple) -> MAT:
    """
    Extract detected card crop.
    Args:
    - img (MatLike): Original image matrix.
    - bbox (tuple): Bounding box coordinates (x1, y1, x2, y2) defining the region to crop.
    Returns:
        MatLike: Cropped image matrix corresponding to the detected card.
    """

    x1, y1, x2, y2 = bbox

    h, w = img.shape[:2]

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    return img[y1:y2, x1:x2]

def _load_images_from_bytearray(raw_images: list[bytearray]) -> list[MAT | None]:
    """
    Load an image from a bytearray (typically from web sources).

    Args:
        - file (bytearray): Raw image bytes.
    Returns:
    - tuple: (image matrix, save path string)
    """
    logger = logging.getLogger(_NAME)
    images: list[MAT | None] = []
    for raw_image in raw_images:
        try:
            image_bytes = np.frombuffer(raw_image, dtype=np.uint8)
            img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("Failed to decode image from byte array")
                images.append(None)
                continue
            images.append(img)
        except Exception as e:
            logger.warning(f"Exception occurred while loading image from byte array: {e}")
            images.append(None)
    return images

def health(raw_images: list[bytearray]) -> tuple[list[str], list[bool]]:
    configure_logger(_NAME, debug=True)
    log = logging.getLogger(_NAME)
    checklist: list[str] = []
    checks: list[bool] = []
    imgs = None
    model = None

    checklist.append("Images loaded successfully")
    try:
        imgs = _load_images_from_bytearray(raw_images)
        checks.append(True)
    except Exception as e:
        log.exception(f"Image loading failed: {e}")
        checks.append(False)
    
    checklist.append("Contours detected and exported as YOLO labels")
    try:
        if imgs is None: raise Exception("No images to process")
        for img in imgs:
            if img is not None:
                approx = _detectContours(img)
                if approx is not None and len(approx) == 4:
                    yolo_img, label = _contourToYOLO(img.copy(), approx)
                    if yolo_img is not None and label:
                        checks.append(True)
                    else:
                        if yolo_img is None:
                            log.warning("YOLO image generation failed for an image")
                        if not label:
                            log.warning("YOLO label generation failed for an image")
                        checks.append(False)
                else:
                    log.warning("Contour detection failed for an image")
                    checks.append(False)
            else:
                log.warning("One of the images is None, skipping contour detection")
                checks.append(False)
    except Exception as e:
        log.exception(f"Contour detection or YOLO label generation failed: {e}")
        checks.append(False)

    checklist.append("YOLO model loaded and inference ran without errors")
    try:
        model = load_yolo_model()
        if imgs is None: raise Exception("No images to process for inference")
        for img in imgs:
            if img is not None:
                results = model.predict(source=[img], conf=0.4, verbose=False)
                if results and results[0].boxes is not None:
                    checks.append(True)
                else:
                    log.warning("YOLO inference did not return valid results for an image")
                    checks.append(False)
            else:
                log.warning("One of the images is None, skipping inference")
                checks.append(False)
    except Exception as e:
        log.exception(f"YOLO model loading or inference failed: {e}")
        checks.append(False)
    return checklist, checks

def run(**kwargs) -> list[dict]:
    """
    """
    debug: bool = kwargs.get('debug', False)
    imgs: list[bytearray] = kwargs.get('imgs', [])
    model: YOLO = load_yolo_model(kwargs.get('model', None))
    # config may come from kwargs so we don't keep loading the config
    config: dict = load_config(_NAME, kwargs.get('config', {}))["detector"]

    conf: float = config['conf']
    iou: float = config['iou']
    batch_size: int = config['batch_size']

    configure_logger(_NAME, debug=debug)
    log = logging.getLogger(_NAME)
    
    valid_images: list[MAT] = []
    valid_indices: list[int] = []
    for i, img in enumerate(_load_images_from_bytearray(imgs)):
        if img is not None:
            valid_images.append(img)
            valid_indices.append(i)

    log.debug(f"Processing {len(valid_images)}/{len(imgs)}, {batch_size} at a time")

    all_results: list[dict] = []

    for batch_start in range(0, len(valid_images), batch_size):
        batch = valid_images[batch_start:batch_start + batch_size]

        results = model.predict(source=batch, conf=conf, iou=iou, verbose=debug)

        for local_idx, result in enumerate(results):
            source_idx = valid_indices[batch_start + local_idx]
            img = batch[local_idx]

            if result.boxes is None: continue

            boxes = result.boxes

            xyxy_list = boxes.xyxy.tolist()
            conf_list = boxes.conf.tolist()
            for det_idx, (coords, conf_score) in enumerate(zip(xyxy_list, conf_list)):
                x1, y1, x2, y2 = map(int, coords)

                if x1 >= x2 or y1 >= y2:
                    log.warning(f"Skipping degenerate bbox ({x1},{y1},{x2},{y2})")
                    continue

                crop = _extractCrop(img, (x1, y1, x2, y2))
                entry: dict = {
                    "source_idx":          source_idx,
                    "detection_idx":       det_idx,
                    "bbox":                (x1, y1, x2, y2),
                    "detector_confidence": float(conf_score),
                    "crop":                crop,
                }
                # if debug:
                #     show_image(crop, f"{_NAME}_crop_{source_idx}_{det_idx}")
                log.debug(
                    f"Image {source_idx} | det {det_idx} | bbox={entry['bbox']} "
                    f"| conf={entry['detector_confidence']:.2f}"
                )
                all_results.append(entry)
    return all_results

def main():
    args = module_arguments(
        desc="Smeargle: Pokémon card image processor for ROI extraction and dataset generation.",
        subcommands={
            "generate": {
                "desc": "Process raw images to generate YOLO-labeled dataset.",
                "args": {
                    "--qa": {"action": "store_true", "help": "Sample a subset of images for manual review."},
                    "--debug": {"action": "store_true", "help": "Save intermediate images"},
                    "--progress": {"action": "store_true", "help": "Show dataset generation progress"},
                }
            },
            "push": {
                "desc": "Split dataset, create YAML, and push to Kaggle.",
                "args": {
                    "--message" : {
                        "type": str, "help": "Commit message", "default": "Update dataset"
                    },
                }
            },
            "run": {
                "desc": "Run inference on raw images using a YOLO model.",
                "args": {
                    "--path": {
                        "type": str, "help": "Path to the raw images folder", "default": _INPUT_DIR
                    },
                    "--model": {
                        "type": str, "help": "Path to the YOLO model file.", "default": _MODEL_PATH
                    },
                    "--conf": {
                        "type": float, "default": 0.4, "help": "Minimum confidence for detections."
                    },
                    "--size": {
                        "type": int, "default": 16, "help": "Number of images in a batch."
                    },
                    "--debug": {
                        "action": "store_true", "help": "Save cropped card images for debugging."
                    }
                }
            },
        }
    )
    if not hasattr(args, "command") or args.command is None:
        print("No command provided. Use --help for usage information.")
        return
    if args.command == "generate":
        generate(qa=args.qa, debug=args.debug, progress=args.progress)
    elif args.command == "push":
        push(args.message)
    elif args.command == "run":
        model = load_yolo_model(args.model)
        imgs: list[bytearray] = []
        if args.path:
            if not os.path.isdir(args.path):
                print(f"Provided path '{args.path}' does not exist or is not a directory.")
                return
            
            for filename in os.listdir(args.path):
                file_path = os.path.join(args.path, filename)
                if os.path.isfile(file_path) and os.path.splitext(filename)[1].lower() in (".jpg", ".jpeg", ".png"):
                    with open(file_path, "rb") as f: imgs.append(bytearray(f.read()))
        results = run(imgs=imgs, model=model, conf=args.conf, size=args.size, debug=args.debug)
        for result in results[:5]: result['crop'] = 'Cannot Show'
        print(results[:5])
    

if __name__ == "__main__":
    main()