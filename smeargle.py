"""
smeagle.py — Aligns and crops Pokémon card images from a folder, extracting the evolution portrait region.

For each image in the `images/` directory:
- Finds the card using edge + contour detection
- Applies a perspective warp to deskew the card
- Extracts the portrait region in the top-left
- Saves debug images to `adjusted-images/<image-name>/`
"""

import cv2
import numpy as np
import os
from pathlib import Path

# -------------------------------
# Configuration
# -------------------------------
INPUT_DIR = "images"
OUTPUT_DIR = "adjusted-images"
CARD_WIDTH, CARD_HEIGHT = 480, 680
ROI_BOX = (40, 45, 60, 60)  # (x, y, width, height)

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
for file in os.listdir(INPUT_DIR):
    if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    image_path = os.path.join(INPUT_DIR, file)
    image_name = Path(file).stem
    save_path = os.path.join(OUTPUT_DIR, image_name)
    os.makedirs(save_path, exist_ok=True)

    print(f"\033[34m[INFO] Processing {file}...\033[0m")

    # Load and preprocess
    img = cv2.imread(image_path)
    assert img is not None, f"\033[31m[ERROR] Could not load image: {image_path}\033[0m"
    cv2.imwrite(os.path.join(save_path, "1_original.jpg"), img)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    cv2.imwrite(os.path.join(save_path, "2_edges.jpg"), edges)

    # Detect contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    card_contour = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(card_contour, True)
    approx = cv2.approxPolyDP(card_contour, 0.02 * peri, True)

    if len(approx) != 4:
        print(f"\033[33m[WARNING] Skipping {file} — could not detect card corners.\033[0m")
        continue

    pts = approx.reshape(4, 2)
    rect = order_points(pts)

    # Visualize and save contour overlay
    debug_img = img.copy()
    cv2.drawContours(debug_img, [approx], -1, (0, 255, 0), 3)
    cv2.imwrite(os.path.join(save_path, "3_contour.jpg"), debug_img)

    # Perspective transform
    dst = np.array([[0, 0], [CARD_WIDTH - 1, 0], [CARD_WIDTH - 1, CARD_HEIGHT - 1], [0, CARD_HEIGHT - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    aligned = cv2.warpPerspective(img, M, (CARD_WIDTH, CARD_HEIGHT), flags=cv2.INTER_LANCZOS4)
    cv2.imwrite(os.path.join(save_path, "4_aligned.jpg"), aligned)

    # Extract ROI (evolution portrait box)
    x, y, w_roi, h_roi = ROI_BOX
    roi = aligned[y:y+h_roi, x:x+w_roi]
    cv2.imwrite(os.path.join(save_path, "5_roi.jpg"), roi)

    print(f"\033[32m[SUCCESS] Saved debug images for {file} to {save_path}\033[0m")
