import pandas as pd
import numpy as np
import itertools
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from orbit.models import DLT
from orbit.diagnostics.metrics import smape
from sklearn.metrics import mean_squared_error

def rmse(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

# Load electricity consumption data
df_elec = pd.read_csv("electricity.csv", parse_dates=["date"], index_col="date", dayfirst=True)
df_elec = df_elec.sort_index().asfreq('MS')

# Load heating degree data
df_hd = pd.read_csv("temp.csv", parse_dates=["date"], index_col="date", dayfirst=True)
df_hd = df_hd.sort_index().asfreq('MS')

# Handle missing or infinite values in df_hd
df_hd = df_hd.replace([np.inf, -np.inf], np.nan).interpolate().fillna(method='bfill')

# Load forecasted heating degree data
forecast_hd = pd.read_csv("heating_degree_forecast.csv", parse_dates=["date"], index_col="date", dayfirst=True)
forecast_hd = forecast_hd.sort_index().asfreq('MS')

# Ensure forecast_hd has exactly 240 rows
date_range = pd.date_range(start=df_elec.index[-1] + pd.DateOffset(months=1), periods=240, freq='MS')
forecast_hd = forecast_hd.reindex(date_range).interpolate(method='linear').fillna(method='bfill')
forecast_hd = forecast_hd.rename_axis("date").reset_index()

# Align df_hd with df_elec to ensure matching lengths
df_hd = df_hd.reindex(df_elec.index, method='nearest')

# Define SARIMAX parameter grid
p = d = q = range(0, 3)
P = D = Q = range(0, 2)
seasonal = [12]
sarima_params = list(itertools.product(p, d, q, P, D, Q, seasonal))

# Sensitivity Analysis for SARIMAX
best_aic = np.inf
best_model = None
for param in sarima_params:
    try:
        model = SARIMAX(df_elec, exog=df_hd, order=param[:3], seasonal_order=param[3:], method="powell")
        result = model.fit(maxiter=500)
        if result.aic < best_aic:
            best_aic = result.aic
            best_model = result
    except:
        continue

# Add noise to heating degree data
noise_levels = [0, 0.01, 0.05, 0.1]
sarimax_results = {}
for noise in noise_levels:
    df_hd_noisy = df_hd + np.random.normal(0, noise, df_hd.shape)
    sarimax_model = SARIMAX(df_elec, exog=df_hd_noisy, order=(4,1,1), seasonal_order=(2,1,2,12), method="powell")
    result = sarimax_model.fit(maxiter=500)
    sarimax_results[noise] = result.aic

# Fit SARIMAX model with updated exogenous formatting
sarimax_model = SARIMAX(df_elec, exog=df_hd, order=(4,1,1), seasonal_order=(2,1,2,12), method="powell")
sarimax_result = sarimax_model.fit(maxiter=500)
forecast_sarimax = sarimax_result.get_forecast(steps=240, exog=forecast_hd.set_index("date"))

# Fit BSTS (DLT) model with adjusted parameters
dlt_model = DLT(
    response_col='billion kilowatthours',
    date_col='date',
    estimator='stan-map',
    seasonality=12,
    seed=42,
    level_sm_input=0.5,  # Increased flexibility
    slope_sm_input=0.4,  # Improved trend capture
    seasonality_sm_input=0.2,  # Adjusted seasonality strength
    num_warmup=1000,
    num_sample=2500
)
dlt_model.fit(df=df_elec.reset_index())
forecast_bsts = dlt_model.predict(df=forecast_hd)

# Sensitivity Analysis for BSTS
bsts_params = [
    (0.3, 0.3, 0.1), (0.5, 0.4, 0.2), (0.7, 0.5, 0.3)  # Different smoothing parameter sets
]
bsts_results = {}
for level, slope, seasonality in bsts_params:
    dlt_model = DLT(response_col='billion kilowatthours', date_col='date', estimator='stan-map', 
                    seasonality=12, seed=42, level_sm_input=level, slope_sm_input=slope, seasonality_sm_input=seasonality,
                    num_warmup=1000, num_sample=2500)
    dlt_model.fit(df=df_elec.reset_index())
    preds = dlt_model.predict(df=forecast_hd)
    bsts_results[(level, slope, seasonality)] = smape(df_elec.iloc[-240:].values.flatten(), preds['prediction'].values.flatten())

# Plot the results
plt.figure(figsize=(12, 6))
plt.plot(df_elec.index, df_elec, label='Historical Data', color='blue')
plt.plot(forecast_sarimax.predicted_mean.index, forecast_sarimax.predicted_mean, label='SARIMAX Forecast', color='red')
plt.plot(forecast_bsts['date'], forecast_bsts['prediction'], label='BSTS Forecast', color='green')
plt.fill_between(forecast_sarimax.predicted_mean.index, 
                 forecast_sarimax.conf_int().iloc[:, 0],
                 forecast_sarimax.conf_int().iloc[:, 1],
                 color='red', alpha=0.1)
plt.xlabel("Year")
plt.ylabel("Billion Kilowatt-Hours")
plt.title("Electricity Consumption Forecast with Heating Degree Days")
plt.legend()
plt.show()

# Evaluate model performance
print("Best SARIMAX AIC:", best_aic)
print("SARIMAX Noise Sensitivity:", sarimax_results)
print("BSTS Parameter Sensitivity:", bsts_results)
print("SARIMAX AIC:", sarimax_result.aic)