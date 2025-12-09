"""
# Porygon
Core model training and dataset management module for PokéPrint Inspector.

This module handles:
- Downloading datasets (including from Kaggle)
- Loading and preprocessing image data
- Splitting datasets into training and test sets
- Building and training a Convolutional Neural Network (CNN) using Keras
- Evaluating model performance
- Visualizing predictions

Dependencies:
- OpenCV (cv2)
- NumPy
- scikit-learn (for train/test splitting)
- TensorFlow/Keras
- kagglehub (for programmatic Kaggle downloads)
- miscellaneous (custom helper functions)

This module is intended to be called from the main execution pipeline and
provides essential ML components for the PyPikachu project.
"""

import cv2
import numpy as np
import os
from sklearn.model_selection import train_test_split
from keras import layers, models, Input
import rotom

def get_dataset(author: str, dataset_name: str, download: bool) -> str:
    """
    Download or extract a dataset, returning the directory path to the dataset.

    Args:
        - TRAINING_DIR (str): Path to save or load the dataset.
        - author (str): Kaggle dataset author.
        - dataset_name (str): Kaggle dataset name.
        - download (bool): Whether to download from Kaggle.
        - use_local_storage (bool): Whether to save Kaggle download locally.

    Returns:
    - str: Path to the dataset directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DATASETS_DIR = str(list(rotom.enviromentals('DATASETS_DIR')).pop())
    DATASETS_DIR = os.path.join(script_dir, DATASETS_DIR)
    DATASETS_DIR = os.path.expanduser(DATASETS_DIR)
    try: os.makedirs(DATASETS_DIR, exist_ok=True)
    except PermissionError as e: rotom.print_with_color(f"Permission denied when creating datasets directory: {str(e)}", 1)
    except Exception as e: rotom.print_with_color(f"Unable to create datasets directory: {str(e)}", 1)
    TRAINING_DIR = os.path.join(DATASETS_DIR, dataset_name)
    TRAINING_DIR = os.path.expanduser(TRAINING_DIR)
    if download:
        try:
            (kaggle_dir_path,) = rotom.enviromentals('KAGGLE_CRED_DIR')
            kaggle_dir_path = os.path.expanduser(kaggle_dir_path)
            os.makedirs(kaggle_dir_path, exist_ok=True)
            kaggle_cred_path = os.path.join(kaggle_dir_path, 'kaggle.json')
            kaggle_cred_path = os.path.expanduser(kaggle_cred_path)
            if not os.path.isfile(kaggle_cred_path):
                with open(kaggle_cred_path, 'w') as f:
                    username, key = rotom.enviromentals('KAGGLE_USERNAME', 'KAGGLE_KEY')
                    f.write(f'{{"username":"{username}","key":"{key}"}}')
            rotom.print_with_color(f"Downloading {author}/{dataset_name} from Kaggle via CLI", 4)
            os.system(f'kaggle datasets download -p {TRAINING_DIR} --unzip {author}/{dataset_name}')
        except Exception as e:
            rotom.print_with_color(f"Unable to download dataset: {str(e)}", 1)
        else:
            rotom.print_with_color("Dataset Download was successful!", 2)
    else:
        # Extract ZIP file if provided
        if os.path.isfile(TRAINING_DIR) and TRAINING_DIR.endswith('.zip'):
            TRAINING_DIR = rotom.extract_zipfile(TRAINING_DIR)
    return TRAINING_DIR

def load_dataset_from_directory(data_dir: str, input_shape: tuple, USE_RGB: bool = True, USE_LOCAL_STORAGE: bool = False) -> tuple[list[cv2.typing.MatLike], list[int], list[str]]:
    """
    Load and label images from a directory.

    Args:
        - data_dir (str): Directory containing images.
        - input_shape (tuple): Target image shape (width, height).
        - USE_RGB (bool): Load as RGB or grayscale.

    Returns:
    - tuple: (X images, y labels, filenames)
    """
    rotom.print_with_color(f"Loading dataset from the directory '{data_dir}'...", 4)
    X = list(); y = list(); file_names = list()
    try:
        for root, _, files in os.walk(data_dir):
            for file in files:
                file_names.append(os.path.join(root, file))
    except:
        rotom.print_with_color(f"Unable to traverse through '{data_dir}'", 1)

    rotom.print_with_color(f"Reading images as {'RGB' if USE_RGB else 'Grayscale'}...", 4)
    for filepath in file_names:
        img = cv2.imread(filepath, cv2.IMREAD_COLOR) if USE_RGB else cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            rotom.print_with_color(f"Could not read image: {filepath}. Skipping...", 3)
            continue
        try:
            img = cv2.resize(img, input_shape)
        except:
            rotom.print_with_color(f"Unable to resize the image {filepath}", 3)
            continue
        else:
            X.append(img)

        try:
            name, _ = os.path.splitext(file)
            label = int(name.split('__')[1])
            y.append(label)
        except (IndexError, ValueError):
            rotom.print_with_color(f"Could not extract label from filename: {file}", 3)
            X.pop()
            continue
    if not USE_LOCAL_STORAGE:
        rotom.print_with_color("Clearing local storage...", 4)
        #rotom.clear_directory(data_dir)
        
    return X, y, file_names

def display_sample(X: list[cv2.typing.MatLike], y: list[int], file_names: list[str], sample_idx: int = 0) -> None:
    """
    Display a sample image and its label.

    Args:
        - X (list): Image data.
        - y (list): Labels.
        - file_names (list): Image file paths.
        - sample_idx (int): Index of the sample to display.
    """
    if X:
        rotom.print_with_color(f"Showing sample image and label: {(file_names[sample_idx])[:20]}, label = {y[sample_idx]}. Press any key to continue...", 4)
        cv2.imshow("Sample Image", X[sample_idx])
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def convert_and_reshape(origX: list[cv2.typing.MatLike], orig_y: list[int], USE_RGB: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert image data to NumPy arrays, normalize, and reshape.

    Args:
        - origX (list): Original image data.
        - orig_y (list): Original labels.
        - USE_RGB (bool): Whether data is RGB or grayscale.

    Returns:
    - tuple: (X as np.ndarray, y as np.ndarray)
    """
    rotom.print_with_color("Converting and reshaping images...", 4)
    try:
        X = np.array(origX, dtype=np.float32) / 255.0
        y = np.array(orig_y)
    except:
        rotom.print_with_color("Unable to convert list of MatLike objects to NumPy Array!", 1)
    else:
        rotom.print_with_color("Conversion was successful.", 2)

    if not USE_RGB:
        try:
            X = X.reshape(-1, 128, 128, 1)  # Add channel dimension
        except:
            rotom.print_with_color("Unable to reshape images!", 1)
            exit()
        else:
            rotom.print_with_color("Images are reshaped.", 2)

    if X.shape != (0,) and y.shape != (0,):
        rotom.print_with_color(f"Dataset shape: {X.shape}, Labels shape: {y.shape}", 4)
    else:
        rotom.print_with_color("The images and/or labels are empty!", 1)

    return X, y

def split_dataset(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Split dataset into training and testing sets.

    Args:
        - X (np.ndarray): Image data.
        - y (np.ndarray): Labels.

    Returns:
    - tuple: (X_train, X_test, y_train, y_test)
    """
    rotom.print_with_color("Splitting dataset into training and testing sets...", 4)
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    except Exception as e:
        rotom.print_with_color(f"Unable to split dataset into training and testing sets. {e}", 1)
    else:
        rotom.print_with_color("Dataset has been split successfully.", 2)
    rotom.print_with_color(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}", 4)
    return X_train, X_test, y_train, y_test

def build_model(num_classes: int, USE_RGB: bool = True) -> models.Sequential:
    """
    Build and compile a simple CNN model.

    Args:
        - num_classes (int): Number of output classes.
        - USE_RGB (bool): Whether input is RGB or grayscale.

    Returns:
    - models.Sequential: Compiled Keras model.
    """
    rotom.print_with_color("Building model...", 4)
    try:
        model = models.Sequential()
        model.add(Input(shape=(128, 128, 3)) if USE_RGB else Input(shape=(128, 128, 1)))
        model.add(layers.Conv2D(8, (3, 3), activation='relu'))
        model.add(layers.Flatten())
        model.add(layers.Dense(num_classes, activation='softmax'))

        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    except Exception as e:
        rotom.print_with_color(f"Failed to build model. {e}", 1)
    else:
        rotom.print_with_color("Model was built successfully", 2)
    return model

def train_model(model: models.Sequential, X_train: np.ndarray, y_train: np.ndarray):
    """
    Train the CNN model.

    Args:
        - model (models.Sequential): Keras model.
        - X_train (np.ndarray): Training images.
        - y_train (np.ndarray): Training labels.

    Returns:
    - History object: Keras training history.
    """
    rotom.print_with_color("Training model...", 4)
    try:
        history = model.fit(X_train, y_train, epochs=3, batch_size=32, validation_split=0.1)
    except Exception as e:
        rotom.print_with_color(f"Model training failed. {e}", 1)
    else:
        rotom.print_with_color("Trained model successfully", 2)
    return history

def evaluate_model(model: models.Sequential, X_test: np.ndarray, y_test: np.ndarray) -> None:
    """
    Evaluate the model on test data.

    Args:
        - model (models.Sequential): Keras model.
        - X_test (np.ndarray): Test images.
        - y_test (np.ndarray): Test labels.
    """
    rotom.print_with_color("Evaluating model...", 4)
    test_loss, test_acc = model.evaluate(X_test, y_test)
    rotom.print_with_color(f"Test accuracy: {test_acc:.4f}, Loss: {test_loss:.4f}", 4)

def predict_and_visualize(model: models.Sequential, images: np.ndarray, labels: np.ndarray = np.array([]), USE_RGB: bool = True, sample_idx: int = 0, verbose: bool = False, testing: bool = False, threshold: float = 0.5):
    """
    Predict and visualize a single test image.

    Args:
        - model (models.Sequential): Keras model.
        - X_test (np.ndarray): Test images.
        - y_test (np.ndarray): Test labels.
        - USE_RGB (bool): Whether images are RGB.
        - sample_idx (int): Index of the sample to visualize.
    """
    rotom.print_with_color("Preparing to make predictions", 4)
    size = images.shape[0]
    channels = 3 if USE_RGB else 1
    img_reshaped = images[sample_idx].reshape((-1, 128, 128, channels)) if testing else images.reshape((-1, 128, 128, channels))
    pred_probs = model.predict(img_reshaped, batch_size=size)
    predicted_classes = np.argmax(pred_probs, axis=1)
    confidences = np.max(pred_probs, axis=1)

    # Apply threshold
    final_preds = []
    for c, p in zip(predicted_classes, confidences):
        if p >= threshold:
            final_preds.append(c)
        else:
            final_preds.append(-1)  # -1 means "uncertain"

    if verbose:
        rotom.show_image(images[sample_idx], "Pokemon")
        rotom.print_with_color(f"Probabilities: {pred_probs}", 4)

    if testing:
        true_label = labels[sample_idx]
        if final_preds[sample_idx] == true_label:
            rotom.print_with_color("The model was right! 🥳", 2)
        elif final_preds[sample_idx] == -1:
            rotom.print_with_color("The model was uncertain 🤔", 3)
        else:
            rotom.print_with_color("Oh no! The model was wrong! 🥺", 1)
        rotom.print_with_color(f"True label: {true_label}, Predicted: {final_preds[sample_idx]}", 4)

    return np.array(final_preds), confidences

def main(defect: str, use_local_storage: bool, use_rgb: bool, kaggle_download: bool, verbose: bool = False):
    args = rotom.parse_JSON_as_arguments(
        'config.json',
        defect,
        ["input_shape", "dataset", "num_classes", "training_dir"])
    
    rotom.clear_terminal()
    TRAINING_DIR = args.get('training_dir', '')

    TRAINING_DIR = get_dataset(
            args.get('author', 'benjaminadedowole'),
            args.get('dataset', 'wartortle-evolution-error'),
            kaggle_download,
            )

    images, labels, filenames = load_dataset_from_directory(TRAINING_DIR, args.get('input_shape', [128, 128]), use_rgb, use_local_storage)
    if verbose: display_sample(images, labels, filenames)
    new_images, new_labels = convert_and_reshape(images, labels)
    training_images, testing_images, training_labels, testing_labels = split_dataset(new_images, new_labels)
    AI = build_model(args.get('num_classes', 2), use_rgb)
    train_model(AI, training_images, training_labels)
    evaluate_model(AI, testing_images, testing_labels)
    predict_and_visualize(AI, testing_images, testing_labels, use_rgb, verbose)
    return AI

if "__main__" == __name__:
    main('wartortle_evolution_error', False, True, True, True)