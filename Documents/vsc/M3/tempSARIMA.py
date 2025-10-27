import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima

# Load the dataset
df = pd.read_csv("temp.csv", parse_dates=["date"], index_col="date")

# Ensure proper date format, sorting, and frequency
df = df.sort_index().asfreq('MS')

# Find optimal SARIMA parameters using auto_arima
auto_model = auto_arima(df["heating_degree"], seasonal=True, m=12, trace=True)
best_order = auto_model.order
best_seasonal_order = auto_model.seasonal_order

# Fit SARIMA model using best parameters
sarima_model = SARIMAX(df["heating_degree"],
                       order=best_order,
                       seasonal_order=best_seasonal_order,
                       enforce_stationarity=False,
                       enforce_invertibility=False)

sarima_fit = sarima_model.fit()

# Forecast future values
forecast_steps = 240  # Forecasting 20 years ahead
forecast = sarima_fit.get_forecast(steps=forecast_steps)

# Ensure forecast index is properly formatted
forecast_index = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq='MS')
forecast_values = forecast.predicted_mean

#Save data to csv to be used in SARIMAX
forecast_df = pd.DataFrame({"month": forecast_index, "heating_degree": forecast_values})
forecast_df.to_csv("heating_degree_forecast.csv", index=False)

# Plot results
plt.figure(figsize=(12, 6))
plt.plot(df.index, df["heating_degree"], label='Historical Data', color='blue')
plt.plot(forecast_index, forecast_values, label='Forecast', color='red')
plt.fill_between(forecast_index, 
                 forecast.conf_int().iloc[:, 0], 
                 forecast.conf_int().iloc[:, 1], 
                 color='pink', alpha=0.3)

plt.title('Heating Degree Forecast')
plt.xlabel('Year')
plt.ylabel('Heating Degree Days')
plt.legend()
plt.show()
