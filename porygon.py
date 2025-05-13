import cv2
import numpy as np
import os
from sklearn.model_selection import train_test_split
from keras import layers, models, Input

USE_RGB = True

# CLear Terminal
os.system('cls' if os.name == 'nt' else 'clear')

# -------------------------------
# Configuration
# -------------------------------
data_dir = "training_data/"
input_shape = (128, 128)
num_classes = 6

# -------------------------------
# Load and label images
# -------------------------------
X = []
y = []

try:
    file_names = os.listdir(data_dir)
except FileNotFoundError:
    print(f"\033[31m[ERROR] No such directory '{data_dir}'\033[0m")
    exit(1)
print(f"\033[34m[INFO] Found {len(file_names)} files in {data_dir}\033[0m")

for file in file_names:
    filepath = os.path.join(data_dir, file)
    
    # Read as grayscale/RGB and resize to match input shape
    img = None
    if USE_RGB:
        img = cv2.imread(filepath, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"\033[33m[WARNING] Could not read image: {filepath}. Skipping...\033[0m")
        continue

    img = cv2.resize(img, input_shape)
    X.append(img)

    try:
        label = int(file.replace(".png", "").split('_')[1])
        y.append(label)
    except (IndexError, ValueError):
        print(f"\033[33m[WARNING] Could not extract label from filename: {file}\033[0m")

# Display a sample
if X:
    print(f"\033[34m[INFO] Showing sample image and label: {file_names[0]}, label = {y[0]}. Press any key to continue...\033[0m")
    cv2.imshow("Sample Image", X[0])
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Convert to NumPy arrays and normalize
X = np.array(X, dtype=np.float32) / 255.0
if not USE_RGB:
    X = X.reshape(-1, 128, 128, 1)  # Add channel dimension
y = np.array(y)

print(f"\033[34m[INFO] Dataset shape: {X.shape}, Labels shape: {y.shape}\033[0m")

# -------------------------------
# Split dataset
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"\033[34m[INFO] Training samples: {len(X_train)}, Test samples: {len(X_test)}\033[0m")

# -------------------------------
# Build model
# -------------------------------
model = models.Sequential()
if USE_RGB:
    model.add(Input(shape=(128, 128, 3)))
else:
    model.add(Input(shape=(128, 128, 1)))
model.add(layers.Conv2D(8, (3, 3), activation='relu'))
model.add(layers.Flatten())
model.add(layers.Dense(num_classes, activation='softmax'))

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

# -------------------------------
# Train model
# -------------------------------
print("\033[34m[INFO] Training model...\033[0m")
history = model.fit(X_train, y_train, epochs=3, batch_size=32, validation_split=0.1)

# -------------------------------
# Evaluate model
# -------------------------------
print("\033[34m[INFO] Evaluating model...\033[0m")
test_loss, test_acc = model.evaluate(X_test, y_test)
print(f"\033[34m[RESULT] Test accuracy: {test_acc:.4f}, Loss: {test_loss:.4f}\033[32m]")

# -------------------------------
# Predict and visualize
# -------------------------------
sample_idx = 1
img = X_test[sample_idx]
true_label = y_test[sample_idx]
if USE_RGB:
    pred_probs = model.predict(img.reshape(1, 128, 128, 3), batch_size=1)
else:
    pred_probs = model.predict(img.reshape(1, 128, 128, 1), batch_size=1)
predicted_class = np.argmax(pred_probs)

print(f"\033[34m[INFO] True label: {true_label}, Predicted: {predicted_class}\033[0m")
print(f"\033[34m[INFO] Probabilities: {pred_probs}\033[0m")

cv2.imshow(f"The hand has {true_label} fingers up", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
if predicted_class == true_label:
    print(f'\033[32m[SUCCESS] The model was right! 🥳\033[0m')
else:
    print(f'\033[31m[FAILURE] Oh No! The model was wrong! 🥺\033[0m')
