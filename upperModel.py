import random
import utils
from Model import Model
import numpy as np
import os
import csiread
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

testDirectory = "Test Data"
trainDirectory = "Train Data"
def buildModel():
    # Creating models for each directory(room) in Training data
    models = []
    directories = [x[0] for x in os.walk(trainDirectory)]
    for dir in directories:
        models.append(Model(dir))

    # Creating a dataset from collected data of multiple filled rooms
    testDataFrame = utils.create_dataset(testDirectory)
    X = testDataFrame['Data']
    y = testDataFrame['hasPerson']
    X = X.apply(utils.preprocess_data)
    X = list(X)

    # Gathering predictions from each model that corresponds to a room
    predictions = []
    for model in models:
        predictions.append(model.trainedModel.predict(X))

    # Transforming the collection of predictions into a comparable format for accuracy test
    transformed_predictions = [[sublist[i][0] for sublist in predictions] for i in range(len(predictions[0]))]
    return transformed_predictions, y




def runUpperModel():
    # Build the upperModel and make predictions
    y_pred, y_test = buildModel()

    # Evaluate the model
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Accuracy: {accuracy}')

    # Optional: Displaying the predictions and actual values
    for i in range(len(y_test)):
        print(f'Actual: {y_test.iloc[i]}, Predicted: {y_pred[i]}')


runUpperModel()