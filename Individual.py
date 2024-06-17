import random
import numpy as np
import os
import csiread
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import MultiLabelBinarizer

import utils
from Model import Model

trainPath = "Training Data/2"
testPath = "Individual test/2"

md = utils.create_dataset(testPath)


utils.IndividualAcc(md, 0.2)


