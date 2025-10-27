from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
import time
from flask_socketio import SocketIO

# Dictionary to track active scrapers and their status
scraper_statuses = {}

# Initialize Socket.IO client
socketio = None

def set_socketio(socket_instance):
    global socketio
    socketio = socket_instance

def stop_scraping(session_id):
    if session_id in scraper_statuses:
        scraper_statuses[session_id]['running'] = False

def start_scraping_with_updates(url, session_id):
    # Initialize status tracking
    scraper_statuses[session_id] = {
        'running': True,
        'last_update': time.time()
    }
    
    # Set up Chrome WebDriver with Service and ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    
    # Configure Chrome options for headless operation
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Create a Chrome WebDriver instance
    driver = webdriver.Chrome(service=service, options=options)
    
    # Navigate to the provided URL
    driver.get(url)
    
    # Initial wait for page to load
    time.sleep(5)
    
    try:
        # Find the dropdown element by its select tag
        dropdown = Select(driver.find_element(By.XPATH, '//div[@class="flexNoWrap"]//select'))
        
        # Continuous scraping loop
        while scraper_statuses[session_id]['running']:
            # Get all options from the dropdown
            options = dropdown.options
            all_results = {}
            
            # Iterate through each event (dropdown option)
            for option in options:
                # Select the event
                dropdown.select_by_visible_text(option.text)
                
                # Wait for the page to update with the new event data
                time.sleep(3)
                
                # Scrape data for this event
                event_results = []
                rows = driver.find_elements(By.XPATH, '//tr[@class="resultsRow tableRow"]')
                
                # Loop through rows and extract data
                for row in rows:
                    try:
                        rank = row.find_element(By.XPATH, './/td[@class="first-cell"]/p').text
                        names = []
                        
                        # Get all names (could be multiple names)
                        name_elements = row.find_elements(By.XPATH, './/td[@class="sticky-column"]/p/span')
                        for name_element in name_elements:
                            names.append(name_element.text)
                        
                        sail_number = row.find_element(By.XPATH, './/td[@class="print_smallPadding"]/span/p').text
                        boat_name = row.find_element(By.XPATH, './/td[4]/p').text
                        club = row.find_element(By.XPATH, './/td[5]/p').text
                        
                        # Dynamically collect race results into a list
                        race_results = []
                        race_cells = row.find_elements(By.XPATH, './/td[@class="centeredText print_smallPadding lessPadding"]/span/p')
                        for race_cell in race_cells:
                            race_results.append(race_cell.text)
                        
                        # Build result object
                        result = {
                            "rank": rank,
                            "names": names,
                            "sail_number": sail_number,
                            "boat": boat_name,
                            "club": club,
                            "race_results": race_results
                        }
                        
                        event_results.append(result)
                    except Exception as e:
                        print(f"Error scraping row: {e}")
                
                # Add event results to the full results dict
                all_results[option.text] = event_results
            
            # Emit results via socketio
            if socketio:
                socketio.emit('scraper_update', {
                    'session_id': session_id,
                    'results': all_results,
                    'timestamp': time.time()
                })
            
            # Wait before next refresh cycle (adjust as needed)
            time.sleep(30)  # Check for updates every 30 seconds
            
            # Refresh the page to get latest data
            driver.refresh()
            time.sleep(5)
            
            # Re-find the dropdown since we refreshed the page
            dropdown = Select(driver.find_element(By.XPATH, '//div[@class="flexNoWrap"]//select'))
    
    except Exception as e:
        # Send error information to the client
        if socketio:
            socketio.emit('scraper_error', {
                'session_id': session_id,
                'error': str(e)
            })
    
    finally:
        # Clean up when stopped
        driver.quit()
        if session_id in scraper_statuses:
            del scraper_statuses[session_id]