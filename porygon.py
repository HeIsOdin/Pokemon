import cv2
import numpy as np
import os
from sklearn.model_selection import train_test_split
from keras import layers, models, Input

USE_RGB = True

# -------------------------------
# Configuration
# -------------------------------
data_dir = "training_data/"
input_shape = (128, 128)
num_classes = 2

def load_dataset_from_directory(data_dir: str) -> tuple[list[cv2.typing.MatLike], list[int], list[str]]:
    # -------------------------------
    # Load and label images
    # -------------------------------
    X = list[cv2.typing.MatLike](); y = list[int]()
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
            name, _ = os.path.splitext(file)
            label = int(name.split('_')[1])
            y.append(label)
        except (IndexError, ValueError):
            print(f"\033[31m[WARNING] Could not extract label from filename: {file}\033[0m")
            exit(1)
    return X, y, file_names

def display_sample(X: list[cv2.typing.MatLike], y: list[int], file_names: list[str], sample_idx: int = 0) -> None:
    # Display a sample
    if X:
        print(f"\033[34m[INFO] Showing sample image and label: {file_names[sample_idx]}, label = {y[sample_idx]}. Press any key to continue...\033[0m")
        cv2.imshow("Sample Image", X[sample_idx])
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def convert_and_reshape(origX: list[cv2.typing.MatLike], orig_y: list[int]) -> tuple[np.ndarray, np.ndarray]:
    # Convert to NumPy arrays and normalize
    X = np.array(origX, dtype=np.float32) / 255.0
    if not USE_RGB:
        X = X.reshape(-1, 128, 128, 1)  # Add channel dimension
    y = np.array(orig_y)
    print(f"\033[34m[INFO] Dataset shape: {X.shape}, Labels shape: {y.shape}\033[0m")
    return X, y

def split_dataset(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # -------------------------------
    # Split dataset
    # -------------------------------
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"\033[34m[INFO] Training samples: {len(X_train)}, Test samples: {len(X_test)}\033[0m")
    return X_train, X_test, y_train, y_test

def build_model() -> models.Sequential:
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
    return model

def train_model(model: models.Sequential, X_train: np.ndarray, y_train: np.ndarray):
    # -------------------------------
    # Train model
    # -------------------------------
    print("\033[34m[INFO] Training model...\033[0m")
    history = model.fit(X_train, y_train, epochs=3, batch_size=32, validation_split=0.1)
    return history

def evaluate_model(model: models.Sequential, X_test: np.ndarray, y_test: np.ndarray) -> None:
    # -------------------------------
    # Evaluate model
    # -------------------------------
    print("\033[34m[INFO] Evaluating model...\033[0m")
    test_loss, test_acc = model.evaluate(X_test, y_test)
    print(f"\033[34m[RESULT] Test accuracy: {test_acc:.4f}, Loss: {test_loss:.4f}\033[0m")

def predict_and_visualize(model: models.Sequential, X_test: np.ndarray, y_test: np.ndarray, sample_idx: int = 1) -> None:
    # -------------------------------
    # Predict and visualize
    # -------------------------------
    img = X_test[sample_idx]
    true_label = y_test[sample_idx]
    if USE_RGB:
        pred_probs = model.predict(img.reshape(1, 128, 128, 3), batch_size=1)
    else:
        pred_probs = model.predict(img.reshape(1, 128, 128, 1), batch_size=1)
    predicted_class = np.argmax(pred_probs)

    print(f"\033[34m[INFO] True label: {true_label}, Predicted: {predicted_class}\033[0m")
    print(f"\033[34m[INFO] Probabilities: {pred_probs}\033[0m")

    cv2.imshow(f"Pokemon", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    if predicted_class == true_label:
        print(f'\033[32m[SUCCESS] The model was right! 🥳\033[0m')
    else:
        print(f'\033[31m[FAILURE] Oh No! The model was wrong! 🥺\033[0m')