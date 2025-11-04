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

def order_points(pts: np.ndarray) -> np.ndarray:
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
        img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(filename=os.path.join(save_path, "1_original.jpg"), img=img)
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
        img = np.zeros((100, 100, 3), dtype=np.uint8)
    return img, save_path

def detect_edges(img: cv2.typing.MatLike, path: str) -> cv2.typing.MatLike:
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

    if path: cv2.imwrite(os.path.join(path, "2_edges.jpg"), edges)
    return edges

def detect_contours(img: cv2.typing.MatLike, edges: cv2.typing.MatLike) -> cv2.typing.MatLike:
    """
    Detect the largest external contour in an edge image.
    
    Args:
        - img (MatLike): Image to be processed.
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

def align_with_orb(img, template, out_wh):
    h, w = out_wh[1], out_wh[0]
    orb = cv2.ORB.create(1500)
    kp1, des1 = orb.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), np.array([]))
    kp2, des2 = orb.detectAndCompute(cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),  np.array([]))
    if des1 is None or des2 is None: return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)[:200]
    if len(matches) < 10: return None
    src = np.array([kp1[m.queryIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    dst = np.array([kp2[m.trainIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if H is None: return None
    return cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LANCZOS4)

def refine_roi_by_ncc(aligned, roi_box, roi_template_path, search=8):
    x,y,w,h = roi_box
    roi_template = cv2.imread(roi_template_path, cv2.IMREAD_COLOR) or np.zeros((h, w, 3), dtype=np.uint8)
    best, best_off = -1.0, (0,0)
    for dy in range(-search, search+1):
        for dx in range(-search, search+1):
            xs, ys = x+dx, y+dy
            patch = aligned[ys:ys+h, xs:xs+w]
            if patch.shape[:2] != (h,w): continue
            res = cv2.matchTemplate(cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY),
                                    cv2.cvtColor(roi_template, cv2.COLOR_BGR2GRAY),
                                    cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            if score > best:
                best, best_off = score, (dx,dy)
    dx,dy = best_off
    return (x+dx, y+dy, w, h), best

def robust_roi(aligned, path, ROI_BOX, ROI_TEMPLATE, search=8):
    # 1) optional local refinement
    box_refined, score = refine_roi_by_ncc(aligned, ROI_BOX, ROI_TEMPLATE, search)
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
        if path:
            cv2.imwrite(os.path.join(path, "6_roi_blurry.jpg"), roi)
        return roi, score, "blurry"
    if score < 0.6:
        if path:
            cv2.imwrite(os.path.join(path, "6_roi_low_template_match.jpg"), roi)
        return roi, score, "low_template_match"
    if path:
            cv2.imwrite(os.path.join(path, "6_roi.jpg"), roi)
    return roi, score, "ok"

def roi_extraction(aligned: np.ndarray, path: str, ROI_BOX: tuple[int, int, int, int], ROI_TEMPLATE: str = 'roi_templates/wartortle_evolution_error.jpg', search: int = 8):
    """
    Extract the defined region of interest (ROI) from an aligned image.

    Args:
        - aligned (MatLike): Aligned card image.
        - save_path (str): Directory to save ROI and debug image.
        - ROI_BOX (tuple): (x, y, width, height) of the region to crop.

    Returns:
    - MatLike: Cropped ROI image.
    """
    # 1) optional local refinement
    box_refined, score = refine_roi_by_ncc(aligned, ROI_BOX, ROI_TEMPLATE, search)
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
        if path:
            cv2.imwrite(os.path.join(path, "6_roi_blurry.jpg"), roi)
        return roi, score, "blurry"
    if score < 0.6:
        if path:
            cv2.imwrite(os.path.join(path, "6_roi_low_template_match.jpg"), roi)
        return roi, score, "low_template_match"
    if path:
            cv2.imwrite(os.path.join(path, "6_roi.jpg"), roi)
    return roi, score, "ok"

def main():
    args = {
        "title": "demo",
        "input_dir": "",
        "debugging_dir": "",
        "dimensions": [480, 680],
        "roi": [40, 45, 60, 60]
    }
    image, path = load_file_from_directory(args.get('title', ''), args.get('input_dir', ''), args.get('debugging_dir', ''))
    image_edges = detect_edges(image, path)
    approx = detect_contours(image, image_edges)
    aligned = draw_contours(image, approx, path, args.get('dimensions', [480, 680]))
    roi, score, status = roi_extraction(aligned, path, args.get('roi', [40, 45, 60, 60]))
    rotom.show_image(roi, f"Score: {score}, Status: {status}")
    return

if __name__ == "__main__":
    main()
