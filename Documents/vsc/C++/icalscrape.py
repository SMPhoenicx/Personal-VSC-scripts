import requests
from icalendar import Calendar
from datetime import datetime
import pytz
import pandas as pd

def fetch_assignments(ical_url):
    """Fetch and parse assignments from iCal feed"""
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/calendar,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Fetch the iCal data with headers
    response = requests.get(ical_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch iCal feed. Status code: {response.status_code}\nResponse: {response.text}")
    
    # Parse the iCal data
    cal = Calendar.from_ical(response.text)
    
    # Store assignments
    assignments = []
    
    # Process each event
    for component in cal.walk():
        if component.name == "VEVENT":
            # Extract the date information
            start_date = component.get('dtstart').dt
            due_date = component.get('dtend').dt
            
            # Convert to datetime if date
            if not isinstance(start_date, datetime):
                start_date = datetime.combine(start_date, datetime.min.time())
            if not isinstance(due_date, datetime):
                due_date = datetime.combine(due_date, datetime.min.time())
                
            # Convert to local time if timezone-aware
            local_tz = pytz.timezone('America/Chicago')  # Adjust for your timezone
            if start_date.tzinfo is not None:
                start_date = start_date.astimezone(local_tz)
            if due_date.tzinfo is not None:
                due_date = due_date.astimezone(local_tz)
            
            assignment = {
                'title': str(component.get('summary', 'No Title')),
                'description': str(component.get('description', 'No Description')),
                'date_assigned': start_date.strftime('%Y-%m-%d %H:%M'),
                'date_due': due_date.strftime('%Y-%m-%d %H:%M'),
                'uid': str(component.get('uid', '')),
            }
            assignments.append(assignment)
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(assignments)
    
    # Sort by due date
    if not df.empty:
        df['date_due'] = pd.to_datetime(df['date_due'])
        df = df.sort_values('date_due')
    
    return df

def main():
    # Your iCal URL
    ical_url = "https://sjs.myschoolapp.com/podium/feed/iCal.aspx?z=4ubN3SKrB8pAx8PiUv8nvUv9eF4pz2HTD5kUmwIL0KVzjZ4Ed0yB3y1XV0ZLBSGNxZWe5SeyYy8gXqZ3HtcAzw%3d%3d"
    try:
        # Fetch and process assignments
        assignments_df = fetch_assignments(ical_url)
        
        if assignments_df.empty:
            print("No assignments found in the feed.")
            return
            
        # Display upcoming assignments
        print("\nUpcoming Assignments:")
        print("--------------------")
        
        for _, row in assignments_df.iterrows():
            print(f"\nAssignment: {row['title']}")
            print(f"Due Date: {row['date_due']}")
            print(f"Assigned: {row['date_assigned']}")
            print(f"Description: {row['description'][:100]}...")  # Show first 100 chars of description
        
        # Save to CSV (optional)
        assignments_df.to_csv('assignments.csv', index=False)
        print("\nAssignments have been saved to 'assignments.csv'")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()