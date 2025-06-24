"""
# Smeargle
Image alignment and Region of Interest(ROI) extraction module for PokéPrint Inspector.

This module processes Pokémon card images by:
- Detecting card edges and contours
- Applying perspective correction to deskew the card
- Extracting the evolution portrait region (ROI) in the top-left
- Saving debug images (original, edges, aligned, ROI) to structured folders

Inputs:
- Local image files from directory
- Bytearray image data from online sources

Outputs:
- Debug and processed images saved in 'adjusted_images/<image-name>/'

Dependencies:
- OpenCV (cv2)
- NumPy
- miscellaneous.py (for colored console logging)

This module is a core component of the PokéPrint Inspector pipeline,
which analyzes card images to detect known Pokémon card defects.
"""

import cv2
import numpy as np
import os
from pathlib import Path
import rotom

def order_points(pts):
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
    return rect

def load_file_from_directory(file: str, INPUT_DIR: str = 'images', OUTPUT_DIR: str = 'adjusted_images'):
    """
    Load an image from a directory and prepare a save path for debug outputs.

    Args:
        - file (str): Filename of the image.
        - INPUT_DIR (str): Input directory path.
        - OUTPUT_DIR (str): Output directory for debug images.

    Returns:
    - tuple: (image matrix, save path string)
    """
    file = file[:40].replace(' ', '_').replace('/', '-') + '.jpg'
    image_path = os.path.join(INPUT_DIR, file)
    image_name = Path(file).stem
    save_path = os.path.join(OUTPUT_DIR, image_name)
    os.makedirs(save_path, exist_ok=True)

    if not os.path.isfile(image_path):
        rotom.print_with_color(f"File '{image_path}' does not exist", 1)

    img = cv2.imread(image_path)
    if img is None:
        rotom.print_with_color(f"Could not load image: {image_path}", 1)
    cv2.imwrite(os.path.join(save_path, "1_original.jpg"), img)
    return img, save_path

def load_file_from_bytearray(file: bytearray, save_path: str):
    """
    Load an image from a bytearray (typically from web sources).

    Args:
        - file (bytearray): Raw image bytes.
        - save_path (str): Directory path to save debug outputs.

    Returns:
    - tuple: (image matrix, save path string)
    """
    image_bytes = np.frombuffer(file, dtype=np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if img is None:
        rotom.print_with_color("Could not load image as bytes", 1)
    return img, save_path

def detect_edges(img: cv2.typing.MatLike, save_path: str) -> cv2.typing.MatLike:
    """
    Convert an image to grayscale, apply blur, and detect edges using Canny.

    Args:
        - img (MatLike): Input image matrix.
        - save_path (str): Directory path to save edge debug image.

    Returns:
    - MatLike: Binary edge map.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    if save_path:
        cv2.imwrite(os.path.join(save_path, "2_edges.jpg"), edges)
    return edges

def detect_contours(img: cv2.typing.MatLike, edges: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """
    Detect the largest external contour in an edge image.

    Args:
        - edges (MatLike): Binary edge map.

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
    edges = detect_edges(img, '')
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
                rotom.print_with_color("[3] Using convex hull fallback", 3)
                return approx
            rect = cv2.minAreaRect(card_contour)
            box = cv2.boxPoints(rect)
            return np.array(box, dtype=np.int32)
    return np.empty((0, 2), dtype=np.int32)


def draw_contours(img: cv2.typing.MatLike, approx: cv2.typing.MatLike, save_path: str, CARD_DIM: tuple[int, int]):
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
    if save_path:
        cv2.imwrite(os.path.join(save_path, "3_contour.jpg"), debug_img)

    # Apply perspective warp
    rect = order_points(pts)
    dst = np.array([[0, 0], [CARD_WIDTH - 1, 0], [CARD_WIDTH - 1, CARD_HEIGHT - 1], [0, CARD_HEIGHT - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    aligned = cv2.warpPerspective(img, M, (CARD_WIDTH, CARD_HEIGHT), flags=cv2.INTER_LANCZOS4)
    if save_path:
        cv2.imwrite(os.path.join(save_path, "4_aligned.jpg"), aligned)
    return aligned

def roi_extraction(aligned: np.ndarray, save_path: str, ROI_BOX: tuple[int, int, int, int]):
    """
    Extract the defined region of interest (ROI) from an aligned image.

    Args:
        - aligned (MatLike): Aligned card image.
        - save_path (str): Directory to save ROI and debug image.
        - ROI_BOX (tuple): (x, y, width, height) of the region to crop.

    Returns:
    - MatLike: Cropped ROI image.
    """
    x, y, w_roi, h_roi = ROI_BOX

    # Draw and save ROI box on aligned image
    aligned_with_box = aligned.copy()
    cv2.rectangle(aligned_with_box, (x, y), (x + w_roi, y + h_roi), (0, 0, 255), 2)
    if save_path:
        cv2.imwrite(os.path.join(save_path, "5_aligned_with_roi.jpg"), aligned_with_box)

    # Extract and save the ROI
    roi = aligned[y:y + h_roi, x:x + w_roi]
    if save_path:
        cv2.imwrite(os.path.join(save_path, "6_roi.jpg"), roi)
    return roi
