import tensorflow as tf
import cv2
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from keras import layers, models

# Our data is in this directory
data_dir = "data/"
file_names = os.listdir(data_dir)
print(file_names[5])

# Initializing two arrays to store the images and labels
X = []
y = []

for file in file_names:
    #print("File name: ", file)
    
    # Reading image using OpenCV and storing it to the array 'X'. It stores each image as an array.
    # cv2 (OpenCV) is a handy Python package used for Computer Vision tasks. We use it to read the images.
    img = cv2.imread(f'{data_dir}/{file}', cv2.IMREAD_GRAYSCALE) 
    X.append(img)
    
    # Label: temporarily remove the file format ".png", then get the label from it.
    # eg. from the file name xyz_0.png, we remove ".png", and get the last character after that.
    label = file.replace(".png", "").split('_')[1]
    #print(label)
    y.append(int(label))
    
    #print("Label from file:", label)

cv2.imshow("First Image", X[0])
cv2.waitKey(0)
cv2.destroyAllWindows()

# When reading using cv2.imread(), the image is read as a numpy array of dimension (height, width, channel)
print(type(X[0]))
y = np.array(y)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2)
X_train = np.array(X_train, dtype=np.float32, ndmin=1)
X_test = np.array(X_test, dtype=np.float32, ndmin=1)
X_train[0].shape

len(X_train), len(y_train)

model = models.Sequential()
model.add(layers.Conv2D(8, (3, 3), activation='relu', input_shape=(128, 128, 1)))
# The first layer is a 2-D Convolutional layer. It has 8 kernels, each of size 3x3. It uses relu activation function
# The first layer in a Keras model requires the shape of input, which in this case is 128x128x1 (a 128x128 greyscale image)

          
model.add(layers.Flatten())
# Flatten() is used to flatten the output from the previous array into a 1-D array.
          
model.add(layers.Dense(6, activation='softmax')) 
# The last layer of a Neural Network should have the same number of nodes as the number of output classes.
# Since the labels are 0, 1, 2, 3, 4 and 5, we define the last layer as having 6 nodes.

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
# Model.compile() is used to configure the learning process before training. Here, we define the optimizer, loss functions and performance metrics.

model.fit(X_train, y_train, epochs=3, batch_size=32)
# Model.fit() is used to train the model. We define how many epochs to train it on, the batch size, 

# Model.evaluate() is used to evaluate the model using the metric defined in model.compile()
print(model.evaluate(X_test, y_test)) 

img = X_test[1]
cv2.imshow("Prediction", img)
print(model.predict(img.reshape(1, 128, 128, 1), batch_size=1))