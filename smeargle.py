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
from cv2.typing import MatLike as IMG # for type hinting only, not an actual import
from logging import Logger as LOGGER  # for type hinting only, not an actual import

import cv2
import numpy as np
import os
import sys
import logging

NAME         = 'Smeargle'
ROI_BOX      = (40, 45, 60, 60)  # Example ROI box (x, y, width, height)
CARD_DIM     = (480, 680)  # Target dimensions for aligned card images
INPUT_DIR    = os.path.join('images', 'input')   # Directory for input images
OUTPUT_DIR   = os.path.join('images', 'output')  # Directory for debug outputs
DATASET_DIR  = os.path.join('images', 'dataset') # Directory for final processed dataset
ROI_TEMPLATE = 'roi_templates/wartortle_evolution_error.jpg'  # Template for NCC refinement

ID                     = 0
MIN_ASPECT_RATIO       = 0.45
MAX_ASPECT_RATIO       = 0.90
MIN_BOX_AREA_RATIO     = 0.20
MAX_BOX_AREA_RATIO     = 0.98
MIN_CONTOUR_AREA_RATIO = 0.10

def __saveImage__(img: IMG, filename: str, stage: int, log: LOGGER) -> str:
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
        if stage == 1: path = os.path.join(path, "1_original.jpg")
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

def __saveForYOLO__(img: IMG, label: str, filename: str, log: LOGGER) -> str:
    """
    Save a YOLO label to disk with error handling.

    Args:
        - label (str): Label string to save.
        - filename (str): Name of the file to save.
        - log (Logger): Logger for debug messages.
    """
    path = os.path.join(DATASET_DIR, os.path.splitext(filename)[0])
    if not os.path.isdir(path):
        log.warning(f"Save path '{path}' does not exist. Creating directory.")
        os.makedirs(path, exist_ok=True)
    try:
        cv2.imwrite(os.path.join(path, "image.jpg"), img)
        cv2.imshow(label, img)
        ch = cv2.waitKey(0)
        cv2.destroyAllWindows()
        if ch == 27:
            log.info(f"User exited during review of '{filename}'")
            sys.exit(0)
        if ch != 13:
            log.warning(f"User rejected YOLO label for '{filename}'")
            return ""
        label_path = os.path.join(path, "label.txt")
        with open(label_path, "w", encoding="utf-8") as f:
            f.write(label + "\n")
        log.debug(f"Saved label to {label_path}")
        return path
    except Exception as e:
        log.error(f"Failed to save label '{path}': {e}")
        return ""

def __orderPoints__(pts: np.ndarray, log: LOGGER) -> np.ndarray:
    """
    Reorder corner points into a consistent top-left, top-right, bottom-right, bottom-left order.

    Args:
        - pts (np.ndarray): Array of shape (4, 2) with unordered points.

    Returns:
    - np.ndarray: Array of shape (4, 2) with ordered points.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]      # Top-left
    rect[2] = pts[np.argmax(s)]      # Bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]   # Top-right
    rect[3] = pts[np.argmax(diff)]   # Bottom-left
    log.debug(f"Ordered points: {rect}")
    return rect

def __loadFileFromDirectory__(filepath: str, log: LOGGER) -> IMG | None:
    """
    Load an image from a directory and prepare a save path for debug outputs.

    Args:
        - file (str): Filename of the image.
        - log (Logger): Logger for debug messages.

    Returns:
    - tuple: (image matrix, save path string)
    """

    image_path = os.path.join(INPUT_DIR, filepath)

    if not os.path.isfile(image_path):
        log.warning(f"Image file '{image_path}' does not exist.")
        return None

    img = cv2.imread(image_path)
    if img is None:
        log.warning(f"Failed to load image '{image_path}'")
        img = np.zeros((100, 100, 3), dtype=np.uint8)
    return img

def __loadFileFromBytearray__(file: bytearray, log: LOGGER):
    """
    Load an image from a bytearray (typically from web sources).

    Args:
        - file (bytearray): Raw image bytes.
        - log (Logger): Logger for debug messages.

    Returns:
    - tuple: (image matrix, save path string)
    """
    image_bytes = np.frombuffer(file, dtype=np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if img is None:
        log.warning(f"Failed to decode image from byte array")
        img = np.zeros((100, 100, 3), dtype=np.uint8)
    return img

def __detectEdges__(img: IMG) -> IMG:
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

def __detectContours__(img: IMG, edges: IMG, log: LOGGER) -> IMG:
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
    edges = __detectEdges__(img)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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

def __contourToYOLO__(image: IMG, approx: np.ndarray, log: LOGGER, ratios: dict[str, float] = {}):
    """
    Convert a 4-point contour into a YOLO axis-aligned bounding-box label.

    Args:
        - image (MatLike): Original image for reference dimensions.
        - approx (np.ndarray): Approximated contour points (should be 4 points).
        - log (Logger): Logger for debug messages.
        - class_id (int): Class ID for YOLO label (default 0).
        - min_contour_area_ratio (float): Minimum contour area ratio to image area to consider valid.
        - min_box_area_ratio (float): Minimum bounding box area ratio to image area to consider valid.
        - max_box_area_ratio (float): Maximum bounding box area ratio to image area to consider valid.
        - min_aspect_ratio (float): Minimum aspect ratio (width/height) to consider valid.
        - max_aspect_ratio (float): Maximum aspect ratio (width/height) to consider valid.

    Returns:
        tuple: (image with drawn contours, YOLO label string) or (None, '') if invalid
    """
    id = int(ratios.get("class_id", ID))
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

    return image, f"{id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"

def __drawContours__(img: IMG, approx: IMG, log: LOGGER) -> tuple[IMG, IMG]:
    """
    Apply a perspective transform to align and deskew the card.

    Args:
        - img (MatLike): Input image matrix.
        - approx (MatLike): Approximated contour points.
        - save_path (str): Directory to save aligned image.
        - CARD_DIM (tuple): Target card dimensions (width, height).

    Returns:
    - MatLike: Aligned, deskewed image.
    """
    pts = approx.reshape(4, 2)
    CARD_WIDTH, CARD_HEIGHT = CARD_DIM

    # Save contour overlay
    debug_img = img.copy()
    cv2.drawContours(debug_img, [approx], -1, (0, 255, 0), 3)

    # Apply perspective warp
    rect = __orderPoints__(pts, log)
    dst = np.array([[0, 0], [CARD_WIDTH - 1, 0], [CARD_WIDTH - 1, CARD_HEIGHT - 1], [0, CARD_HEIGHT - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    aligned = cv2.warpPerspective(img, M, (CARD_WIDTH, CARD_HEIGHT), flags=cv2.INTER_LANCZOS4)
    return debug_img, aligned

def __alignWithOrb__(img: IMG, template, out_wh, log: LOGGER) -> IMG | None:
    h, w = out_wh[1], out_wh[0]
    orb = cv2.ORB.create(1500)
    kp1, des1 = orb.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), np.array([]))
    kp2, des2 = orb.detectAndCompute(cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),  np.array([]))
    if des1 is None or des2 is None: return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)[:200]
    if len(matches) < 10:
        log.warning(f"Not enough ORB matches found: {len(matches)}")
        return None
    src = np.array([kp1[m.queryIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    dst = np.array([kp2[m.trainIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if H is None:
        log.warning("Homography could not be computed")
        return None
    return cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LANCZOS4)

def __refineROIByNCC__(aligned: IMG, log: LOGGER, search: int = 8):
    x, y, w, h = ROI_BOX

    roi_template = cv2.imread(ROI_TEMPLATE, cv2.IMREAD_COLOR)
    if roi_template is None:
        log.warning(f"Could not load ROI template '{ROI_TEMPLATE}'. Using a blank fallback template.")
        roi_template = np.zeros((h, w, 3), dtype=np.uint8)
    else:
        try:
            roi_template = cv2.resize(roi_template, (w, h), interpolation=cv2.INTER_AREA)
        except Exception as e:
            log.warning(f"Could not resize ROI template '{ROI_TEMPLATE}': {e}. Using blank fallback template.")
            roi_template = np.zeros((h, w, 3), dtype=np.uint8)

    best = -1.0
    best_off = (0, 0)

    aligned_h, aligned_w = aligned.shape[:2]

    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            xs, ys = x + dx, y + dy
            xe, ye = xs + w, ys + h

            if xs < 0 or ys < 0 or xe > aligned_w or ye > aligned_h:
                continue

            patch = aligned[ys:ye, xs:xe]
            if patch.shape[:2] != (h, w):
                log.warning(
                    f"Skipping patch at ({dx},{dy}) due to size mismatch: {patch.shape[:2]} vs {(h, w)}"
                )
                continue

            try:
                patch_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(roi_template, cv2.COLOR_BGR2GRAY)
                res = cv2.matchTemplate(patch_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                score = float(res.max())
            except Exception as e:
                log.warning(f"NCC failed at offset ({dx},{dy}): {e}")
                continue

            if score > best:
                log.debug(f"New best NCC score: {score:.4f} at offset ({dx},{dy})")
                best = score
                best_off = (dx, dy)

    dx, dy = best_off
    return (x + dx, y + dy, w, h), best

def __robustROI__(aligned: IMG, log: LOGGER, search=8):
    # 1) optional local refinement
    box_refined, score = __refineROIByNCC__(aligned, log, search)
    x,y,w,h = box_refined
    roi = aligned[y:y+h, x:x+w]

    # 2) normalize (helps classifier)
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4))
    l = clahe.apply(l)
    roi = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)

    # 3) quality gates (simple examples)
    if cv2.Laplacian(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 20:
        return roi, score, "blurry"
    if score < 0.6: return roi, score, "low_template_match"
    return roi, score, "ok"

def __roiExtraction__(aligned: np.ndarray, log: LOGGER, search: int = 8):
    """
    Extract the defined region of interest (ROI) from an aligned image.

    Args:
        - aligned (MatLike): Aligned card image.
        - ROI_BOX (tuple): (x, y, width, height) of the region to crop.

    Returns:
    - MatLike: Cropped ROI image.
    """
    # 1) optional local refinement
    box_refined, score = __refineROIByNCC__(aligned, log, search)
    x,y,w,h = box_refined
    roi = aligned[y:y+h, x:x+w]

    # 2) normalize (helps classifier)
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4))
    l = clahe.apply(l)
    roi = cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)

    # 3) quality gates (simple examples)
    if cv2.Laplacian(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 20:
        return roi, score, "blurry"
    if score < 0.6: return roi, score, "low_template_match"
    return roi, score, "ok"

def main():
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"

    logger = LOGGER(NAME)
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
    if not os.path.isdir(INPUT_DIR) or len([f for f in os.listdir(INPUT_DIR)]) < 5:
        logger.warning(f"{INPUT_DIR} has too few images. Running Spinarak to populate it...")
        spinarak_main(debug=True, queries=queries, threshold=threshold)

    if not INPUT_DIR or not os.path.isdir(INPUT_DIR):
        raise Exception(f"Input directory '{INPUT_DIR}' does not exist or is not a directory.")

    image_files = sorted(
        file for file in os.listdir(INPUT_DIR)
        if str(file).lower().endswith((".jpg", ".jpeg", ".png"))
    )
    logger.debug(f"Found {len(image_files)} image files in '{INPUT_DIR}'")

    if not image_files: raise Exception(f"No image files found in directory '{INPUT_DIR}'")

    for file in image_files:
        try:
            image = __loadFileFromDirectory__(file, logger)
            if image is None:
                logger.warning(f"Skipping '{file}' due to load failure.")
                continue

            if debug: __saveImage__(image, file, 1, logger)

            if image is None or image.size == 0:
                logger.warning(f"Skipping '{file}' because it is empty or could not be loaded.")
                continue

            image_edges = __detectEdges__(image)
            if debug: __saveImage__(image_edges, file, 2, logger)

            approx = __detectContours__(image, image_edges, logger)

            if len(approx) != 4:
                logger.warning(f"Skipping '{file}' because card corners could not be detected.")
                continue

            yolo_img, label = __contourToYOLO__(image.copy(), approx, logger)

            if yolo_img is not None and label:
                __saveForYOLO__(yolo_img, label, file, logger)
            else:
                logger.warning(f"Failed to export YOLO label for '{file}'")

            # debug_img, aligned = __drawContours__(image, approx, logger)
            # if debug: __saveImage__(debug_img, file, 3, logger)
            # if debug: __saveImage__(aligned, file, 4, logger)

            # roi, score, status = __roiExtraction__(aligned, logger)
            # if roi is None or roi.size == 0:
            #     logger.warning(f"ROI extraction failed for '{file}'")
            #     results.append({
            #         "file": file,
            #         "status": "roi_extraction_failed",
            #         "score": None,
            #     })
            #     continue

            # if debug:
            #     if status == "ok":
            #         logger.info(f"ROI extraction successful for '{file}' with score {score:.4f}")
            #     elif status == "blurry":
            #         logger.warning(f"ROI for '{file}' is blurry. Score: {score:.4f}")
            #     elif status == "low_template_match":
            #         logger.warning(f"ROI for '{file}' has low template match score. Score: {score:.4f}")

            # if debug: __saveImage__(roi, file, 5, logger)

            # results.append({
            #     "file": file,
            #     "status": status,
            #     "score": float(score),
            #     "accepted": status == "ok",
            # })

            # if status == "ok":
            #     logger.info(f"Processed '{file}' successfully. Score: {score:.4f}")
            # else:
            #     logger.warning(f"ROI status for {file} was '{status}'. Score: {score:.4f}",)

        except Exception as e:
            logger.warning(f"Failed to process '{file}': {e}")

if __name__ == "__main__":
    main()