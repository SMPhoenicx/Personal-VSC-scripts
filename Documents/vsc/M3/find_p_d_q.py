import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima
from orbit.models import DLT  # Bayesian Structural Time Series
from orbit.diagnostics.plot import plot_predicted_data

# Load electricity dataset
df_elec = pd.read_csv("electricity.csv")
df_elec["date"] = pd.to_datetime(df_elec["date"], format="%b %Y")
df_elec.set_index("date", inplace=True)
df_elec = df_elec.sort_index().asfreq('MS')

# Load heating degree dataset (Ensure it's preprocessed similarly)
df_hd = pd.read_csv("temp.csv")
df_hd["date"] = pd.to_datetime(df_hd["date"], format="%b %Y")
df_hd.set_index("date", inplace=True)
df_hd = df_hd.sort_index().asfreq('MS')

# Align datasets (Keep only common time range for training)
df = df_elec.join(df_hd, how="inner").dropna()

# Find optimal SARIMAX parameters with heating degree days as exogenous variable
auto_model = auto_arima(df["billion kilowatthours"], 
                        exogenous=df[["heating_degree"]],  # Add exogenous variable
                        seasonal=True, m=12, trace=True)
best_order = auto_model.order
best_seasonal_order = auto_model.seasonal_order

print(best_order)
print(best_seasonal_order)