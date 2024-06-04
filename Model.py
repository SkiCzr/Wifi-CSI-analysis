import utils
import random
import numpy as np
import os
import csiread
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Class that contains all the details of a model trained on one room
class Model:
    def __init__(self, folderName):
        self.folderName = folderName
        self.trainDataFrame = utils.create_dataset(folderName)
        self.trainedModel = self.trainModel()


    def trainModel(self):
        dataset = self.trainDataFrame
        X = dataset['Data']
        y = dataset['hasPerson']

        X = X.apply(utils.preprocess_data)

        # Converting to list of lists or arrays for model compatibility
        X = list(X)

        # Instantiate and train the model
        model = RandomForestClassifier()
        model.fit(X, y)
        return model
