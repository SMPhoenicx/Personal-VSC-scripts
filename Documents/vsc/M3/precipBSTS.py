import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from orbit.models import DLT
from orbit.diagnostics.plot import plot_predicted_data

# Load the dataset
df = pd.read_csv("precipitation.csv", parse_dates=["date"], index_col="date")

# Ensure proper date format, sorting, and frequency
df = df.sort_index().asfreq('MS')

# Define the DLT model
dlt_model = DLT(
    response_col='precipitation',
    date_col='date',
    estimator='stan-map',
    seasonality=12,
    seed=42,
    level_sm_input=0.5,  # Adjusted smoothing parameters
    slope_sm_input=0.3,
    seasonality_sm_input=0.2,
    num_warmup=1000,
    num_sample=2500
)

# Fit DLT model
dlt_model.fit(df=df.reset_index())

# Forecast future values
forecast_steps = 300  # Adjusting to forecast beyond 20 years
future_dates = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq='MS')
forecast_df = pd.DataFrame({"date": future_dates})
forecast = dlt_model.predict(df=forecast_df)

# Save data to csv to be used in SARIMAX
forecast_df["precipitation"] = forecast["prediction"]
forecast_df.to_csv("precipitation_forecast.csv", index=False)

# Plot results
plt.figure(figsize=(12, 6))
plt.plot(df.index, df["precipitation"], label='Historical Data', color='blue')
plt.plot(forecast_df["date"], forecast_df["precipitation"], label='Forecast', color='red')

# Fix: Use the correct column names for confidence intervals
plt.fill_between(forecast_df["date"], 
                 forecast["prediction_5%"], 
                 forecast["prediction_95%"], 
                 color='pink', alpha=0.3)

plt.title('Precipitation Forecast')
plt.xlabel('Year')
plt.ylabel('Precipitation')
plt.legend()
plt.show()