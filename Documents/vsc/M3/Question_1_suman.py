import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C


def init_model():
    # 1. Load Data from CSV
    # CSV Format: Time, Temperature
    data = pd.read_csv("temperature_data.csv")


    # Convert Time to Hour Index (0-23)
    data["Hour"] = pd.to_datetime(data["Time"], format="%I:%M %p").dt.hour
    X = data["Hour"].values.reshape(-1, 1)  # Time Points
    y = data["Temperature"].values  # Temperature Values


    # 2. Define the Kernel (Smooth RBF Kernel)
    kernel = C(1.0) * RBF(length_scale=5.0)


    # 3. Fit the Gaussian Process Model
    gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
    gpr.fit(X, y)

    return gpr

    # # 4. Make Predictions on a Fine Time Grid
    # X_fine = np.linspace(0, 23, 500).reshape(-1, 1)  # Smooth Grid from 0 to 23 Hours
    # y_pred, sigma = gpr.predict(X_fine, return_std=True)
    


# Function to Get Outdoor Temperature at Any Hour
def Tout(gpr, hour):
    hour = np.array([[hour]])
    temp, _ = gpr.predict(hour, return_std=True)
    return temp[0]





