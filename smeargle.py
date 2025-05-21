"""
Aligns and crops Pokémon card images from a folder, extracting the evolution portrait region.

For each image in the `images/` directory:
- Finds the card using edge + contour detection
- Applies a perspective warp to deskew the card
- Extracts the portrait region in the top-left
- Saves debug images to `adjusted_images/<image-name>/`
"""

import cv2
import numpy as np
import os
from pathlib import Path
import miscellaneous

# -------------------------------
# Utility: Order Points
# -------------------------------
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]      # Top-left
    rect[2] = pts[np.argmax(s)]      # Bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]   # Top-right
    rect[3] = pts[np.argmax(diff)]   # Bottom-left
    return rect

# -------------------------------
# Process Each Image
# -------------------------------
def load_file_from_directory(file: str, INPUT_DIR: str='images', OUTPUT_DIR: str='adjusted_images'):
    file = file[:40].replace(' ', '_').replace('/', '-')+'.jpg'
    image_path = os.path.join(INPUT_DIR, file)
    image_name = Path(file).stem
    save_path = os.path.join(OUTPUT_DIR, image_name)
    os.makedirs(save_path, exist_ok=True)

    # Load and preprocess
    if not os.path.isfile(image_path):
        miscellaneous.print_with_color(f"File '{image_path}' does not exist", 1)

    img = cv2.imread(image_path)
    if img is None:
        miscellaneous.print_with_color(f"Could not load image: {image_path}", 1)
    cv2.imwrite(os.path.join(save_path, "1_original.jpg"), img)
    return img, save_path

def load_file_from_bytearray(file: bytearray, save_path: str):
    image_bytes = np.asarray(file, dtype=np.uint8)
    img = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if img is None:
        miscellaneous.print_with_color("Could not load image as bytes", 1)
    return img, save_path

def detect_edges(img: cv2.typing.MatLike, save_path: str) -> cv2.typing.MatLike:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    if save_path:
        cv2.imwrite(os.path.join(save_path, "2_edges.jpg"), edges)
    return edges

def detect_contours(edges: cv2.typing.MatLike):
    # Detect contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    card_contour = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(card_contour, True)
    approx = cv2.approxPolyDP(card_contour, 0.02 * peri, True)
    return approx

def draw_contours(img: cv2.typing.MatLike, approx: cv2.typing.MatLike, save_path: str, CARD_DIM: tuple[int, int]):
    pts = approx.reshape(4, 2)
    CARD_WIDTH, CARD_HEIGHT = CARD_DIM
    # Visualize and save contour overlay
    debug_img = img.copy()
    cv2.drawContours(debug_img, [approx], -1, (0, 255, 0), 3)
    if save_path:
        cv2.imwrite(os.path.join(save_path, "3_contour.jpg"), debug_img)

    rect = order_points(pts)
    # Perspective transform
    dst = np.array([[0, 0], [CARD_WIDTH - 1, 0], [CARD_WIDTH - 1, CARD_HEIGHT - 1], [0, CARD_HEIGHT - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    aligned = cv2.warpPerspective(img, M, (CARD_WIDTH, CARD_HEIGHT), flags=cv2.INTER_LANCZOS4)
    if save_path:
        cv2.imwrite(os.path.join(save_path, "4_aligned.jpg"), aligned)
    return aligned

def roi_extraction(aligned: cv2.typing.MatLike, save_path: str, ROI_BOX: tuple[int, int, int, int]):
    x, y, w_roi, h_roi = ROI_BOX
    aligned_with_box = aligned.copy()
    cv2.rectangle(aligned_with_box, (x, y), (x + w_roi, y + h_roi), (0, 0, 255), 2)  # Red border around ROI
    if save_path:
        cv2.imwrite(os.path.join(save_path, "5_aligned_with_roi.jpg"), aligned_with_box)

    # Extract ROI (evolution portrait box)
    roi = aligned[y:y+h_roi, x:x+w_roi]
    if save_path:
        cv2.imwrite(os.path.join(save_path, "6_roi.jpg"), roi)
    return roi
