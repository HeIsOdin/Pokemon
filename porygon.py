import cv2
import numpy as np
import os
from sklearn.model_selection import train_test_split
from keras import layers, models, Input
import miscellaneous
import kagglehub

def get_dataset(TRAINING_DIR: str, author: str, dataset_name: str):
    _, download = miscellaneous.make_a_choice(f"Download dataset '{author}/{dataset_name}' using Kagglehub (Kaggle API key required!)? Y/n: ", 'n')
    
    if download:
        path = ''
        try:
            kagglehub.login()
            os.environ["KAGGLEHUB_CACHE"] = f"{dataset_name}"
            miscellaneous.print_with_color(f"Downloading {author}/{dataset_name} from Kaggle", 4)
            path = kagglehub.dataset_download(f"{author}/{dataset_name}")
        except Exception as e:
            miscellaneous.print_with_color(f"Unable to download dataset: {str(e)}", 1)
        else:
            miscellaneous.print_with_color("Dataset Download was successful!", 2)
            dataset_name = path
    else:
        dataset_name, _ = miscellaneous.make_a_choice('Enter the path to the dataset: ', dataset_name)

    if not os.path.exists(dataset_name):
        return dataset_name

    # If the dataset is a ZIP file, extract it
    if dataset_name.endswith('.zip'):
        miscellaneous.extract_zipfile(dataset_name, TRAINING_DIR)
    return dataset_name

def load_dataset_from_directory(data_dir: str, input_shape: tuple, USE_RGB: bool = True) -> tuple[list[cv2.typing.MatLike], list[int], list[str]]:
    # -------------------------------
    # Load and label images
    # -------------------------------
    miscellaneous.print_with_color(f"Loading dataset from the directory '{data_dir}'...'", 4)
    X = list[cv2.typing.MatLike](); y = list[int](); file_names = list[str]()
    try:
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith((".jpg", ".png", ".jpeg")):
                    file_names.append(os.path.join(root, file))
    except:
        miscellaneous.print_with_color(f"Unable to transverse through '{data_dir}'", 1)

    miscellaneous.print_with_color(f"Reading images as {'RGB' if USE_RGB else 'Grayscale'}...", 4)
    for filepath in file_names:

        # Read as grayscale/RGB and resize to match input shape
        img = cv2.imread(filepath, cv2.IMREAD_COLOR) if USE_RGB else cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            miscellaneous.print_with_color(f"Could not read image: {filepath}. Skipping...", 3)
            continue

        try:
            img = cv2.resize(img, input_shape)
        except:
            miscellaneous.print_with_color(f"Unable to resize the image {filepath}", 3)
            continue
        else:
            X.append(img)

        try:
            name, _ = os.path.splitext(file)
            label = int(name.split('__')[1])
            y.append(label)
        except (IndexError, ValueError):
            miscellaneous.print_with_color(f"Could not extract label from filename: {file}", 3)
            X.pop()
            continue
    return X, y, file_names

def display_sample(X: list[cv2.typing.MatLike], y: list[int], file_names: list[str], sample_idx: int = 0) -> None:
    # Display a sample
    if X:
        miscellaneous.print_with_color(f"Showing sample image and label: {(file_names[sample_idx])[:10]}, label = {y[sample_idx]}. Press any key to continue...", 4)
        cv2.imshow("Sample Image", X[sample_idx])
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def convert_and_reshape(origX: list[cv2.typing.MatLike], orig_y: list[int], USE_RGB: bool = True) -> tuple[np.ndarray, np.ndarray]:
    # Convert to NumPy arrays and normalize
    miscellaneous.print_with_color("Converting and reshaping images...", 4)
    try:
        X = np.array(origX, dtype=np.float32) / 255.0
        y = np.array(orig_y)
    except:
        miscellaneous.print_with_color("Unable to convert list of MatLike objects to NumPy Array!", 1)
    else:
        miscellaneous.print_with_color("Conversion was successful.", 2)

    if not USE_RGB:
        try:
            X = X.reshape(-1, 128, 128, 1)  # Add channel dimension
        except:
            miscellaneous.print_with_color("Unable to reshape images!", 1)
            exit()
        else:
            miscellaneous.print_with_color("Images are reshaped.", 2)

    if X.shape != (0,) and y.shape != (0,):
        miscellaneous.print_with_color(f"Dataset shape: {X.shape}, Labels shape: {y.shape}", 4)
    else:
        miscellaneous.print_with_color("The images and/or labels are empty!", 1)

    return X, y

def split_dataset(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # -------------------------------
    # Split dataset
    # -------------------------------
    miscellaneous.print_with_color("Splitting dataset into training and testing sets...", 4)
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    except Exception as e:
        miscellaneous.print_with_color(f"Unable to split dataset into training and testing sets. {e}", 1)
    else:
        miscellaneous.print_with_color("Dataset has been split successfully.", 2)
    miscellaneous.print_with_color(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}", 4)
    return X_train, X_test, y_train, y_test

def build_model(num_classes: int, USE_RGB: bool = True) -> models.Sequential:
    miscellaneous.print_with_color("Building model...", 4)
    # -------------------------------
    # Build model
    # -------------------------------
    try:
        model = models.Sequential()
        model.add(Input(shape=(128, 128, 3))) if USE_RGB else model.add(Input(shape=(128, 128, 1)))
        model.add(layers.Conv2D(8, (3, 3), activation='relu'))
        model.add(layers.Flatten())
        model.add(layers.Dense(num_classes, activation='softmax'))

        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    except Exception as e:
        miscellaneous.print_with_color(f"Failed to build model. {e}", 1)
    else:
        miscellaneous.print_with_color(f"Model was built successful", 2)
    return model

def train_model(model: models.Sequential, X_train: np.ndarray, y_train: np.ndarray):
    # -------------------------------
    # Train model
    # -------------------------------
    miscellaneous.print_with_color("Training model...", 4)
    try:
        history = model.fit(X_train, y_train, epochs=3, batch_size=32, validation_split=0.1)
    except Exception as e:
        miscellaneous.print_with_color(f"Model training failed. {e}", 1)
    else:
        miscellaneous.print_with_color(f"Trained Model Successfully", 2)
    return history

def evaluate_model(model: models.Sequential, X_test: np.ndarray, y_test: np.ndarray) -> None:
    # -------------------------------
    # Evaluate model
    # -------------------------------
    miscellaneous.print_with_color("Evaluating model...", 4)
    test_loss, test_acc = model.evaluate(X_test, y_test)
    miscellaneous.print_with_color(f"Test accuracy: {test_acc:.4f}, Loss: {test_loss:.4f}", 4)

def predict_and_visualize(model: models.Sequential, X_test: np.ndarray, y_test: np.ndarray, sample_idx: int = 1, USE_RGB: bool = True) -> None:
    # -------------------------------
    # Predict and visualize
    # -------------------------------
    miscellaneous.print_with_color("Preparing to make predictions", 4)
    img = X_test[sample_idx]
    true_label = y_test[sample_idx]
    pred_probs = model.predict(img.reshape(1, 128, 128, 3), batch_size=1) if USE_RGB else model.predict(img.reshape(1, 128, 128, 1), batch_size=1)
    predicted_class = np.argmax(pred_probs)

    miscellaneous.print_with_color(f"True label: {true_label}, Predicted: {predicted_class}", 4)
    miscellaneous.print_with_color(f"Probabilities: {pred_probs}", 4)

    cv2.imshow(f"Pokemon", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    miscellaneous.print_with_color("The model was right! 🥳", 2) if predicted_class == true_label else miscellaneous.print_with_color("Oh No! The model was wrong! 🥺", 1)
