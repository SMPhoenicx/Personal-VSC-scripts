import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from orbit.models import DLT
from orbit.diagnostics.plot import plot_predicted_data
from orbit.diagnostics.metrics import smape

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

# Fit SARIMAX model with updated exogenous formatting
sarimax_model = SARIMAX(df_elec, exog=df_hd, order=(4,1,1), seasonal_order=(2,1,2,12))
sarimax_result = sarimax_model.fit()
forecast_sarimax = sarimax_result.get_forecast(steps=240, exog=forecast_hd.set_index("date"))

# Fit BSTS (DLT) model with adjusted parameters
dlt_model = DLT(
    response_col='billion kilowatthours',
    date_col='date',
    estimator='stan-map',
    seasonality=12,
    seed=42,
    level_sm_input=0.5,  
    slope_sm_input=0.4,  
    seasonality_sm_input=0.2,  
    num_warmup=1000,
    num_sample=2500
)
dlt_model.fit(df=df_elec.reset_index())
forecast_bsts = dlt_model.predict(df=forecast_hd)

# Extract peak values for 2025, 2030, and 2045
def find_peak_demand(forecast, years):
    peak_values = {}
    for year in years:
        yearly_data = forecast[(forecast.index.year == year)]
        if not yearly_data.empty:
            peak_values[year] = yearly_data.max()
    return peak_values

# Convert BSTS forecast date column to datetime index
forecast_bsts['date'] = pd.to_datetime(forecast_bsts['date'])
forecast_bsts.set_index('date', inplace=True)

# Get peak demand values
years = [2030, 2035, 2045]
sarimax_peaks = find_peak_demand(forecast_sarimax.predicted_mean, years)
bsts_peaks = find_peak_demand(forecast_bsts['prediction'], years)

# Create a results table
peak_demand_table = pd.DataFrame({
    "Year": years,
    "SARIMAX Peak Demand (Billion kWh)": [sarimax_peaks.get(year, np.nan) for year in years],
    "BSTS Peak Demand (Billion kWh)": [bsts_peaks.get(year, np.nan) for year in years]
})

# Display the table
print(peak_demand_table)

# Plot the results
plt.figure(figsize=(12, 6))
plt.plot(df_elec.index, df_elec, label='Historical Data', color='blue')
plt.plot(forecast_sarimax.predicted_mean.index, forecast_sarimax.predicted_mean, label='SARIMAX Forecast', color='red')
plt.plot(forecast_bsts.index, forecast_bsts['prediction'], label='BSTS Forecast', color='green')
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
print("SARIMAX AIC:", sarimax_result.aic)
