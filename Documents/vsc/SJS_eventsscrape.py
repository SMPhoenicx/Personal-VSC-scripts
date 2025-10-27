# ensure these libraries are installed...
# pip3 install icalendar
# pip3 install pandas
# pip3 install requests

from icalendar import Calendar
import pandas as pd
import requests
# ENSURE YOU USE HTTPS NOT WEBCAL
ics_url = "https://sjs.myschoolapp.com/podium/feed/iCal.aspx?z=DDAr4MngSh%2fzItk0SVkyxFK2Cjh3b1P9NmMK2nLpKH5hbBJqTuUT0hRIyZgHc%2f4Mad2dsWy5vMerWPWrr%2fAd2w%3d%3d"  
#headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/calendar,application/calendar,text/plain,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}
#gets the ICS file from the URL
response = requests.get(ics_url, headers=headers)
response.raise_for_status()  # Raise an exception for bad status codes
#create calendar
calendar = Calendar.from_ical(response.text)

# Filter and export events that DON'T start with "Day"
event_list = []

for component in calendar.walk():
    if component.name == "VEVENT":
        summary = str(component.get('summary', ''))
        if summary and not summary.startswith('Day'):
            event_list.append(component)

print(len(event_list))
print(event_list)

event_names = []
dates = []

for event in event_list:
    #gets the event's date
    date = str(event.get('dtstart').dt)
    #gets the date in YYYY-MM-DD format
    date = date[:date.index('T')] if 'T' in date else date
    #gets event info
    event_name = str(event.get('summary'))
    
    event_names.append(event_name)
    dates.append(date)

# Save to .csv file
data = {"Event": event_names, "Date": dates}
df = pd.DataFrame(data)

print(f"All non-Day events:")
print(df)

file_path = "SJS_Events.csv"
df.to_csv(file_path, index=False)