import random
import numpy as np
import os
import csiread
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
# Folder that contains data to train the model
scans_folder = "Training Data/1"

# Gets the name of a csi file and gets all the complex number matrices of all the packets of that specific file
def get_csi(csifile):
    if os.path.isfile(csifile):
        try:
            csi = csiread.Picoscenes(csifile, {'CSI': [52, 2, 1], 'MPDU': 1522})
            csi.read()
            return csi.raw['CSI']['CSI']
        except IndexError as e:
            pass
    return 0


# Method that reads the names of csi files and creates a list of csi data files
def read_files(path):
    file_names = [path + "/" + file for file in os.listdir(path)]
    csi_files = []
    for file_name in file_names:
        csi_files.append(get_csi(file_name))
    return file_names, csi_files



# Function that creates a dataset from the csi files in directory data_folder
def create_dataset(data_folder):
    file_names, csi_files = read_files(data_folder)
    data = []
    for file_index, file in enumerate(csi_files):
        for pack_index, packet in enumerate(file):
            pack = []
            # Taking the state of the room in the csi file(True - has person, False - does not have person)
            # pack.append(file_names[file_index].split("/")[-1][18:-1].split(".")[0].split("_"))
            pack.append(file_names[file_index].split("/")[-1][18:-1].split(".")[0])
            if len(pack[-1]) == 1:
                pack[-1] = pack[-1][0]
            stats = []
            for complex in packet:
                stats.append((np.abs(complex[0])[0], np.angle(complex[0])[0]))
                stats.append((np.abs(complex[1])[0], np.angle(complex[1])[0]))
            pack.append(stats)
            data.append(pack)
    random.shuffle(data)
    df = pd.DataFrame(data, columns=['hasPerson', 'Data'])
    return df



# Preprocessing: Converting list of tuples to a flattened list or array
def preprocess_data(data):
    return [item for sublist in data for item in sublist]


def IndividualAcc(dataset, test_sz):
    # Splitting data into features and labels
    X = dataset['Data']
    y = dataset['hasPerson']
    for index, entry in enumerate(y):
        if entry == ['False', 'False']:
            y[index] = 'FF'
        if entry == ['True', 'False']:
            y[index] = 'TF'
        if entry == ['False', 'True']:
            y[index] = 'FT'
        if entry == ['True', 'True']:
            y[index] = 'TT'
    # Splitting into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_sz, random_state=42)
    X_train = X_train.apply(preprocess_data)
    X_test = X_test.apply(preprocess_data)

    # Converting to list of lists or arrays for model compatibility
    X_train = list(X_train)
    X_test = list(X_test)

    # Instantiate and train the model
    model = RandomForestClassifier()
    print(y_train)
    print(X_train)
    model.fit(X_train, y_train)

    # Make predictions
    y_pred = model.predict(X_test)

    # Evaluate the model
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Accuracy: {accuracy}')
