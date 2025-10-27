import pandas as pd
import re

# Read the data
data = pd.read_csv("precipitation.csv")

# Function to extract month and year from date strings
def extract_month_year(date_str):
    # Create regex patterns to identify the different date formats
    pattern1 = re.compile(r"^(\d+)/(\d+)$")                # matches "1/1"
    pattern2 = re.compile(r"^(\d+)/(\d{4})$")              # matches "2/1997"
    pattern3 = re.compile(r"^(\d+)/(\d+)/(\d{4})$")        # matches "3/1/1997"
    
    if pattern1.match(date_str):
        month, _ = pattern1.match(date_str).groups()
        return int(month), None
    
    elif pattern2.match(date_str):
        month, year = pattern2.match(date_str).groups()
        return int(month), int(year)
    
    elif pattern3.match(date_str):
        month, _, year = pattern3.match(date_str).groups()
        return int(month), int(year)
    
    return None, None

# Preprocess to determine the year pattern
current_year = 1997  # Starting year based on the first entry
months = []
years = []

for _, row in data.iterrows():
    month, year = extract_month_year(row['date'])
    
    # If it's January and no year specified, increment the year
    if month == 1 and year is None:
        current_year += 1
    
    # If the year is explicitly given, update current_year
    if year is not None:
        current_year = year
    
    months.append(month)
    years.append(current_year)

# Create formatted dates
formatted_dates = []
for month, year in zip(months, years):
    if month is not None:
        formatted_dates.append(f"{month:02d}-01-{year}")
    else:
        formatted_dates.append("Invalid date")

# Update the dataframe
data['date'] = formatted_dates

# Save the cleaned data
data.to_csv("precipitation_cleaned.csv", index=False)

# Display sample of the cleaned data
print(data.head(20))