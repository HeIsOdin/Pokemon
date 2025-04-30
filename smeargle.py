"""
smeagle.py — Aligns and crops a Pokémon card image to extract the evolution portrait region.

- Finds the card in the image using edge + contour detection
- Applies a perspective warp to deskew the card
- Extracts a region in the top-left (evolution portrait area)
"""

import cv2
import numpy as np

# -------------------------------
# Load and preprocess image
# -------------------------------
img = cv2.imread("images/best_picture.jpg")
assert img is not None, "❌ Could not load image. Check the path."

print("[INFO] Original image shape:", img.shape)

# Convert to grayscale and apply blur
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blur = cv2.GaussianBlur(gray, (5, 5), 0)

# Edge detection
edges = cv2.Canny(blur, 50, 150)
cv2.imshow("Edges", edges)
cv2.waitKey(0)

# -------------------------------
# Detect card contour
# -------------------------------
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"[INFO] Found {len(contours)} contours.")

# Use the largest contour as the card
card_contour = max(contours, key=cv2.contourArea)
peri = cv2.arcLength(card_contour, True)
approx = cv2.approxPolyDP(card_contour, 0.02 * peri, True)

if len(approx) != 4:
    raise Exception(f"❌ Could not detect card corners — found {len(approx)} points.")

pts = approx.reshape(4, 2)
print("[INFO] Card corner points:\n", pts)

# Visualize the detected contour
debug_img = img.copy()
cv2.drawContours(debug_img, [approx], -1, (0, 255, 0), 3)
cv2.imshow("Detected Card Outline", debug_img)
cv2.waitKey(0)

# -------------------------------
# Order corner points (TL, TR, BR, BL)
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

rect = order_points(pts)
print("[INFO] Ordered points:\n", rect)

# -------------------------------
# Warp card to upright rectangle
# -------------------------------
(w, h) = (480, 680)  # Target size for aligned card
dst = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype="float32")

M = cv2.getPerspectiveTransform(rect, dst)
aligned = cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_LANCZOS4)  # Higher-quality interpolation

cv2.imshow("Aligned Card", aligned)
cv2.waitKey(0)

# -------------------------------
# Crop evolution portrait region
# -------------------------------
x, y, w_roi, h_roi = 40, 45, 60, 60  # Fine-tuned based on aligned image layout
portrait = aligned[y:y+h_roi, x:x+w_roi]

# Draw rectangle on aligned image
cv2.rectangle(aligned, (x, y), (x+w_roi, y+h_roi), (0, 0, 255), 2)
cv2.imshow("Aligned Card with ROI", aligned)
cv2.imshow("Evolution Portrait", portrait)

cv2.waitKey(0)
cv2.destroyAllWindows()
