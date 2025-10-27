from playwright.async_api import async_playwright
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs

from base_scraper import BaseScraper, ScraperType, ScraperMode, ScraperFactory

logger = logging.getLogger(__name__)

class ClubSpotAPIScraper(BaseScraper):
    """
    Optimized API scraper focused on discovery functionality
    Removes unused functions like format_results, fetch_api_data, etc.
    """
    
    def __init__(self, mode: ScraperMode = ScraperMode.SINGLE):
        super().__init__(ScraperType.API, mode)
        self.api_urls = {}
        self.dropdown_combinations = []
        self.current_combination = None
        self.api_requests = {}
        self.max_retries = 3
        self.base_retry_delay = 1.0
        self.connection_timeout = 30
        self.page_load_timeout = 45000  # Playwright timeout in ms
        self.network_idle_timeout = 5000  # ms to wait for network idle
        
        # Multi-user session variables
        self.shared_session_key = None
        self.is_shared_session = False
        self.connected_clients = set()
    
    async def discover_dropdown_combinations(self, page) -> List[List[Dict[str, str]]]:
        """Discover all dropdown combinations on the page"""
        combinations = []
        try:
            # Find all dropdown elements
            dropdowns = await page.query_selector_all('select')
            if not dropdowns:
                logger.info("No dropdowns found, treating as single view")
                return [[]]  # Return empty combination for single view

            # Get options for each dropdown
            dropdown_options = []
            for i, dropdown in enumerate(dropdowns):
                options = await dropdown.query_selector_all('option')
                valid_options = []
                for option in options:
                    value = await option.get_attribute('value')
                    text = await option.text_content()
                    if value and text and text.lower() not in ['select', 'choose', '-- select --']:
                        valid_options.append({'value': value, 'text': text})
                if valid_options:
                    dropdown_options.append(valid_options)

            # Generate all combinations
            if dropdown_options:
                def generate_combinations(current_combo, remaining_options):
                    if not remaining_options:
                        combinations.append(current_combo.copy())
                        return
                    for option in remaining_options[0]:
                        current_combo.append(option)
                        generate_combinations(current_combo, remaining_options[1:])
                        current_combo.pop()

                generate_combinations([], dropdown_options)

            logger.info(f"Discovered {len(combinations)} dropdown combinations")
            return combinations

        except Exception as e:
            logger.error(f"Error discovering dropdown combinations: {e}")
            return [[]]  # Return default empty combination
    
    async def discover(self, url: str) -> bool:
        """
        Discover API URLs for all dropdown combinations
        Main discovery method called by the base class
        """
        return await self.discover_api_urls(url)
        
    async def discover_api_urls(self, results_url: str) -> bool:
        """Use Playwright to discover API URLs with connection reliability"""
        async def _discover_operation():
            browser = None
            try:
                async with async_playwright() as p:
                    # Launch browser with better error handling
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']  # Better for server environments
                    )
                    
                    context = await browser.new_context(
                        user_agent=self.headers['User-Agent']
                    )
                    
                    page = await context.new_page()
                    
                    # Set timeouts
                    page.set_default_navigation_timeout(self.page_load_timeout)
                    page.set_default_timeout(self.connection_timeout * 1000)
                    
                    # Reset state
                    self.api_requests = {}
                    self.current_combination = None

                    async def handle_request(request):
                        """Monitor and capture API requests with error handling"""
                        try:
                            if self.current_combination is not None:
                                url = request.url
                                if "clubspot-results" in url and "boatClassIDs" in url:
                                    combo_key = json.dumps(self.current_combination)
                                    self.api_requests[combo_key] = {
                                        'url': url,
                                        'params': dict(parse_qs(urlparse(url).query))
                                    }
                        except Exception as e:
                            logger.warning(f"Error handling request: {e}")

                    page.on("request", handle_request)

                    # Navigate with retry logic
                    logger.info(f"Navigating to: {results_url}")
                    await page.goto(results_url, wait_until='networkidle')
                    
                    # Check connection health after navigation
                    if not await self.check_connection_health(page):
                        raise Exception("Connection health check failed after navigation")

                    # Get all dropdown combinations
                    self.dropdown_combinations = await self.discover_dropdown_combinations(page)

                    # Try each combination with better error handling
                    for i, combo in enumerate(self.dropdown_combinations):
                        try:
                            if self.should_stop():
                                logger.info("Stop requested during discovery")
                                break
                                
                            self.current_combination = combo
                            logger.debug(f"Processing combination {i+1}/{len(self.dropdown_combinations)}: {combo}")
                            
                            if combo:  # If not empty combination
                                # Select each dropdown value with validation
                                for j, option in enumerate(combo):
                                    # Ensure option is a dict with 'value' key
                                    if isinstance(option, dict) and 'value' in option:
                                        option_value = option['value']
                                    else:
                                        option_value = str(option)
                                    
                                    # Validate dropdown exists before interacting
                                    dropdown_count = await page.evaluate('document.querySelectorAll("select").length')
                                    if j >= dropdown_count:
                                        logger.warning(f"Dropdown {j} not found, skipping")
                                        continue
                                    
                                    await page.evaluate(f"""
                                        const select = document.querySelectorAll('select')[{j}];
                                        if (select) {{
                                            select.value = '{option_value}';
                                            select.dispatchEvent(new Event('change'));
                                        }}
                                    """)
                                    
                                    # Wait for network activity to settle
                                    await page.wait_for_load_state('networkidle', timeout=self.network_idle_timeout)

                            # Wait for any API requests with timeout
                            await asyncio.sleep(2)

                        except Exception as e:
                            logger.error(f"Error processing combination {combo}: {e}")
                            continue

                    # Store discovered API URLs
                    self.api_urls = self.api_requests
                    await self.update_activity()
                    
                    logger.info(f"Discovery completed: {len(self.api_urls)} API URLs found")
                    return len(self.api_urls) > 0

            except Exception as e:
                logger.error(f"Error in discovery operation: {e}")
                raise
            finally:
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass

        try:
            # Use retry logic for the entire discovery operation
            return await self.retry_with_backoff(_discover_operation)
            
        except Exception as e:
            logger.error(f"Discovery failed after retries: {e}")
            await self.emit_error(f"Discovery failed: {str(e)}", "discovery")
            return False
    
    async def scrape_single(self, url: str) -> Dict[str, Any]:
        """
        Single scrape operation with multi-user session support
        """
        try:
            # Generate session key for potential sharing
            self.shared_session_key = self.generate_session_key(url)
            
            # Check if we should join an existing shared session (this would be handled by session manager)
            # For now, proceed with discovery
            
            success = await self.discover(url)
            
            if success:
                # Format the response to match expected structure
                formatted_api_urls = {}
                for combo_key, api_info in self.api_urls.items():
                    formatted_api_urls[combo_key] = {
                        "url": api_info['url'],
                        "params": api_info['params']
                    }
                
                result = {
                    "api_urls": formatted_api_urls,
                    "combinations": self.dropdown_combinations,
                    "metadata": {
                        "total_urls": len(formatted_api_urls),
                        "total_combinations": len(self.dropdown_combinations),
                        "scraped_at": datetime.now().isoformat(),
                        "source_url": url,
                        "session_key": self.shared_session_key,
                        "client_count": self.get_client_count()
                    }
                }
                
                return result
            else:
                # Try graceful degradation
                logger.warning("Primary discovery failed, attempting graceful degradation")
                return await self.handle_poor_connection()
                
        except Exception as e:
            logger.error(f"Error in single scrape: {e}")
            # Try graceful degradation before giving up
            try:
                return await self.handle_poor_connection(url)
            except:
                raise e
    
    def get_discovery_results(self) -> Dict[str, Any]:
        """
        Get the current discovery results without running discovery again
        Used by the /discover-only endpoint
        """
        formatted_api_urls = {}
        for combo_key, api_info in self.api_urls.items():
            formatted_api_urls[combo_key] = {
                "url": api_info['url'],
                "params": api_info['params']
            }
        
        return {
            "api_urls": formatted_api_urls,
            "combinations": self.dropdown_combinations
        }
    async def check_connection_health(self, page) -> bool:
        """Check if the browser connection is healthy"""
        try:
            # Simple connectivity test
            await page.evaluate('navigator.onLine')
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False
        
    async def retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_retry_delay * (2 ** attempt)
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {e}")
                    await self.safe_sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries} attempts: {e}")
        
        if last_exception:
            raise last_exception
        else:
            raise Exception("Operation failed after all retries")
    def generate_session_key(self, url: str) -> str:
        """Generate a session key for multi-user session sharing"""
        import hashlib
        # Create a key based on URL and scraper type for session sharing
        key_data = f"clubspot_api:{url}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def add_client(self, client_id: str):
        """Add a client to this shared session"""
        self.connected_clients.add(client_id)
        logger.info(f"Client {client_id} joined shared session {self.shared_session_key}")

    def remove_client(self, client_id: str):
        """Remove a client from this shared session"""
        self.connected_clients.discard(client_id)
        logger.info(f"Client {client_id} left shared session {self.shared_session_key}")

    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.connected_clients)
    
    async def handle_poor_connection(self, url: str = "") -> Dict[str, Any]:
        """Handle poor connection scenarios with graceful degradation"""
        try:
            # Return cached results if available
            if self.api_urls:
                logger.info("Using cached API URLs due to poor connection")
                return self.get_discovery_results()
            
            # If no cache and we have a URL, try with extended timeouts
            if url:
                original_timeout = self.page_load_timeout
                original_network_timeout = self.network_idle_timeout
                
                # Extend timeouts for poor connection
                self.page_load_timeout = 60000  # 60 seconds
                self.network_idle_timeout = 10000  # 10 seconds
                
                try:
                    logger.info("Retrying discovery with extended timeouts due to poor connection")
                    success = await self.discover(url)
                    if success:
                        return self.get_discovery_results()
                finally:
                    # Restore original timeouts
                    self.page_load_timeout = original_timeout
                    self.network_idle_timeout = original_network_timeout
            
            # If still no success, return minimal response structure
            logger.warning("Graceful degradation: returning minimal response")
            return {
                "api_urls": {},
                "combinations": [],
                "metadata": {
                    "total_urls": 0,
                    "total_combinations": 0,
                    "scraped_at": datetime.now().isoformat(),
                    "error": "Poor connection - unable to discover APIs",
                    "degraded_mode": True
                }
            }
                
        except Exception as e:
            logger.error(f"Graceful degradation failed: {e}")
            # Return minimal response structure as last resort
            return {
                "api_urls": {},
                "combinations": [],
                "metadata": {
                    "total_urls": 0,
                    "total_combinations": 0,
                    "scraped_at": datetime.now().isoformat(),
                    "error": f"Connection failed: {str(e)}",
                    "degraded_mode": True
                }
            }
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection and session status"""
        return {
            "session_key": self.shared_session_key,
            "is_shared": self.is_shared_session,
            "connected_clients": self.get_client_count(),
            "api_urls_cached": len(self.api_urls),
            "combinations_available": len(self.dropdown_combinations),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "error_count": self.error_count,
            "status": self.status.value
        }

# Register the scraper with the factory
ScraperFactory.register_scraper('clubspot_api', ClubSpotAPIScraper)
