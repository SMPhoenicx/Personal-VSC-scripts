from playwright.async_api import async_playwright
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin

from base_scraper import BaseScraper, ScraperType, ScraperMode, ScraperFactory, ScraperStatus

logger = logging.getLogger(__name__)

class RegattaNetworkScraper(BaseScraper):
    """
    Scraper for Regatta Network results pages
    Extracts event information, divisions, and race results
    """
    
    def __init__(self, mode: ScraperMode = ScraperMode.SINGLE):
        super().__init__(ScraperType.HTML, mode)
        self.max_retries = 3
        self.base_retry_delay = 2.0
        self.connection_timeout = 30
        self.page_load_timeout = 30000  # 30 seconds
        self.last_results = {}  # Cache for comparison
        
    async def discover(self, url: str) -> bool:
        """
        Discovery phase - validate URL and check if page loads
        Returns True if the regatta page is accessible
        """
        try:
            # Ensure URL has media_format=1 parameter
            if "media_format=1" not in url:
                if "?" in url:
                    url += "&media_format=1"
                else:
                    url += "?media_format=1"
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers['User-Agent']
                )
                page = await context.new_page()
                
                try:
                    await page.goto(url, timeout=self.page_load_timeout)
                    
                    # Check if this is a valid regatta results page
                    title_element = await page.query_selector("h4")
                    if title_element:
                        title_text = await title_element.text_content()
                        if title_text and any(keyword in title_text.upper() for keyword in ["SERIES", "REGATTA", "CHAMPIONSHIP"]):
                            logger.info(f"Successfully discovered regatta page: {title_text.strip()}")
                            return True
                    
                    logger.warning("Page doesn't appear to be a valid regatta results page")
                    return False
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Discovery failed for {url}: {e}")
            return False
    
    async def scrape_single(self, url: str) -> Dict[str, Any]:
        """
        Single scrape operation - extract regatta data once
        """
        try:
            # Ensure URL has media_format=1 parameter
            if "media_format=1" not in url:
                if "?" in url:
                    url += "&media_format=1"
                else:
                    url += "?media_format=1"
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers['User-Agent']
                )
                page = await context.new_page()
                
                try:
                    await page.goto(url, timeout=self.page_load_timeout)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Extract all data
                    event_info = await self.extract_event_info(page)
                    divisions = await self.extract_divisions(page, url)
                    
                    result = {
                        "event_info": event_info,
                        "divisions": divisions,
                        "metadata": {
                            "scraped_at": datetime.now().isoformat(),
                            "source_url": url,
                            "total_divisions": len(divisions),
                            "scraper_type": "regatta_network"
                        }
                    }
                    
                    # Cache results for comparison in live mode
                    self.last_results = result.copy()
                    
                    return result
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Error in single scrape: {e}")
            await self.emit_error(f"Scraping failed: {str(e)}", "scraping")
            raise e
    
    async def extract_event_info(self, page) -> Dict[str, Any]:
        """Extract event information from the page header"""
        event_info: dict[str, Optional[str]] = {
            "logo_url": None,
            "title": None,
            "club_name": None,
            "dates": None
        }
        
        try:
            # Extract logo URL
            logo_img = await page.query_selector("table.responsive img")
            if logo_img:
                logo_src = await logo_img.get_attribute("src")
                if logo_src:
                    # Convert relative URLs to absolute
                    if logo_src.startswith("//"):
                        event_info["logo_url"] = "https:" + logo_src
                    elif logo_src.startswith("/"):
                        event_info["logo_url"] = "https://www.regattanetwork.com" + logo_src
                    else:
                        event_info["logo_url"] = logo_src
            
            # Extract title and club information
            title_element = await page.query_selector("td[valign='bottom'] h4")
            if title_element:
                title_text = await title_element.text_content()
                if title_text:
                    # Parse title text which contains event name, dates, and club
                    lines = [line.strip() for line in title_text.split('\n') if line.strip()]
                    if lines:
                        # First line is usually the event title with dates
                        first_line = lines[0]
                        event_info["title"] = first_line
                        
                        # Extract dates if present
                        date_match = re.search(r'([A-Za-z]+ \d{1,2}-?\d{0,2},? \d{4})', first_line)
                        if date_match:
                            event_info["dates"] = date_match.group(1)
                        
                        # Second line often contains club name
                        if len(lines) > 1:
                            club_line = lines[1].replace('|', '').strip()
                            if club_line:
                                event_info["club_name"] = club_line
            
            logger.info(f"Extracted event info: {event_info['title']} at {event_info['club_name']}")
            
        except Exception as e:
            logger.warning(f"Error extracting event info: {e}")
        
        return event_info
    
    async def extract_divisions(self, page, base_url: str) -> List[Dict[str, Any]]:
        """Extract all racing divisions and their results"""
        divisions = []
        
        try:
            # Find all division headers (h2 elements with division names)
            division_headers = await page.query_selector_all("h2")
            
            for header in division_headers:
                try:
                    division_data = await self.extract_single_division(page, header, base_url)
                    if division_data:
                        divisions.append(division_data)
                except Exception as e:
                    logger.warning(f"Error extracting division: {e}")
                    continue
            
            logger.info(f"Extracted {len(divisions)} divisions")
            
        except Exception as e:
            logger.error(f"Error extracting divisions: {e}")
        
        return divisions
    
    async def extract_single_division(self, page, header_element, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract a single division's data"""
        try:
            # Get division name and boat count
            header_text = await header_element.text_content()
            if not header_text:
                return None
            
            # Parse division name and boat count
            division_name = None
            boat_count = 0
            races_scored = None
            
            # Extract division name (first part before parentheses)
            name_match = re.search(r'^([^(]+)', header_text.strip())
            if name_match:
                division_name = name_match.group(1).strip()
            
            # Extract boat count
            boat_match = re.search(r'\((\d+) boats?\)', header_text)
            if boat_match:
                boat_count = int(boat_match.group(1))
            
            # Extract races scored info
            races_match = re.search(r'(\d+) races? scored', header_text)
            if races_match:
                races_scored = int(races_match.group(1))
            
            if not division_name:
                return None
            
            # Find the next h4 element (contains last updated info)
            next_h4 = None
            next_element = header_element
            for _ in range(10):  # Limit search to avoid infinite loop
                next_element = await page.evaluate_handle("el => el.nextElementSibling", next_element)
                if not next_element:
                    break
                tag_name = await next_element.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "h4":
                    next_h4 = next_element
                    break
            
            # Extract last updated time
            last_updated = None
            if next_h4:
                h4_text = await next_h4.text_content()
                if h4_text and "last updated" in h4_text.lower():
                    # Extract timestamp
                    time_match = re.search(r'last updated:\s*([^<]+)', h4_text, re.IGNORECASE)
                    if time_match:
                        last_updated = time_match.group(1).strip()
            
            # Extract results table
            results = await self.extract_division_results(page, header_element)
            
            division_data = {
                "name": division_name,
                "boat_count": boat_count,
                "races_scored": races_scored,
                "last_updated": last_updated,
                "results": results,
                "metadata": {
                    "extracted_at": datetime.now().isoformat()
                }
            }
            
            logger.debug(f"Extracted division: {division_name} ({boat_count} boats, {len(results)} results)")
            return division_data
            
        except Exception as e:
            logger.error(f"Error extracting single division: {e}")
            return None
    
    async def extract_division_results(self, page, header_element) -> List[Dict[str, Any]]:
        """Extract results table for a division"""
        results = []
        
        try:
            # The results structure is more complex - we need to look for font elements
            # and track position numbers separately
            current_element = header_element
            position = 1  # Start counting positions
            
            # Skip through elements until we find results or hit next division
            for _ in range(100):  # Increased limit to find more results
                current_element = await page.evaluate_handle("el => el.nextElementSibling", current_element)
                if not current_element:
                    break
                
                # Check if this is the start of the next division
                tag_name = await current_element.evaluate("el => el.tagName.toLowerCase()")
                if tag_name == "h2":
                    break
                
                # Look for font elements containing results
                if tag_name == "font":
                    font_text = await current_element.text_content()
                    if font_text and self.looks_like_result_line(font_text):
                        result_data = self.parse_result_line(font_text, position)
                        if result_data:
                            results.append(result_data)
                            position += 1
                
                # Also check for font elements within table cells or other containers
                font_elements = await current_element.query_selector_all("font")
                for font_elem in font_elements:
                    font_text = await font_elem.text_content()
                    if font_text and self.looks_like_result_line(font_text):
                        result_data = self.parse_result_line(font_text, position)
                        if result_data:
                            results.append(result_data)
                            position += 1
            
            logger.info(f"Found {len(results)} results for division")
            
        except Exception as e:
            logger.warning(f"Error extracting division results: {e}")
        
        return results
    
    def looks_like_result_line(self, text: str) -> bool:
        """Check if a text line looks like a race result"""
        if not text.strip():
            return False
        
        stripped = text.strip()
        
        # Skip header rows - check for common header words
        header_words = ['pos', 'sail', 'boat', 'skipper', 'results', 'points', 'total', 'race', 'click', 'detailed', 'last updated']
        if any(word in stripped.lower() for word in header_words):
            # Additional check: if it contains "Pos" and "Sail" it's definitely a header
            if 'pos' in stripped.lower() and 'sail' in stripped.lower():
                return False
        
        # Look for the pattern: number/text, text, text, race_results ; points
        # Should contain commas and semicolon
        if ',' in stripped and ';' in stripped:
            # Should have at least 3 comma-separated parts before semicolon
            before_semicolon = stripped.split(';')[0]
            parts = before_semicolon.split(',')
            if len(parts) >= 3:
                # Make sure first part looks like a sail number (not "Pos")
                first_part = parts[0].strip()
                if first_part.lower() not in header_words:
                    return True
        
        # Alternative: just commas (some results might not have points)
        if stripped.count(',') >= 2:
            # Check if it doesn't look like header text
            parts = stripped.split(',')
            first_part = parts[0].strip()
            if (first_part.lower() not in header_words and 
                not any(word in stripped.lower() for word in header_words)):
                return True
        
        return False
    
    def parse_result_line(self, text: str, position: int) -> Optional[Dict[str, Any]]:
        """Parse a single result line into structured data"""
        try:
            # Clean up the text - remove extra whitespace and HTML entities
            cleaned = re.sub(r'\s+', ' ', text.strip())
            cleaned = cleaned.replace('&nbsp;', ' ').strip()
            
            # Pattern: Sail, Boat, Skipper, Results ; Total Points
            # Example: "219, Deja' Vu, Steve Mettler, 1-3-1-1-2- ; 8"
            
            # Split by semicolon to separate results from total points
            if ';' in cleaned:
                result_part, points_part = cleaned.rsplit(';', 1)
                total_points = points_part.strip()
                # Remove any trailing HTML or whitespace from points
                total_points = re.sub(r'[^\d\.\,]', '', total_points).strip()
            else:
                result_part = cleaned
                total_points = None
            
            # Parse the result part: Sail, Boat, Skipper, Race Results
            parts = [part.strip() for part in result_part.split(',')]
            
            if len(parts) < 3:
                logger.debug(f"Not enough parts in result line: {parts}")
                return None
            
            sail_number = parts[0] if parts[0] else None
            boat_name = parts[1] if len(parts) > 1 and parts[1] else None
            skipper = parts[2] if len(parts) > 2 and parts[2] else None
            
            # Race results are usually the last part(s) before the semicolon
            race_results = None
            if len(parts) > 3:
                # Join remaining parts as race results
                race_results = ','.join(parts[3:]).strip()
                # Clean up race results (remove trailing commas/dashes)
                race_results = re.sub(r'[-,\s]+$', '', race_results)
                if not race_results:
                    race_results = None
            
            result = {
                "position": position,
                "sail_number": sail_number,
                "boat_name": boat_name,
                "skipper": skipper,
                "race_results": race_results,
                "total_points": total_points
            }
            
            logger.debug(f"Parsed result: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Error parsing result line '{text}': {e}")
            return None
    
    async def scrape_live(self, url: str, update_interval: float = 15.0):
        """
        Live scraping with 15-second intervals
        Continuously monitors for changes and emits updates
        """
        try:
            # Debug logging to check socketio setup
            logger.info(f"Starting regatta network live scraping")
            logger.info(f"Socketio instance: {self.socketio is not None}")
            logger.info(f"Session ID: {self.session_id}")
            logger.info(f"URL: {url}")
            
            if not self.socketio:
                logger.error("CRITICAL: No socketio instance - cannot emit updates")
                await self.emit_error("No socketio instance available", "setup")
                return
            
            if not self.session_id:
                logger.error("CRITICAL: No session_id - cannot emit updates")
                await self.emit_error("No session_id available", "setup")
                return
            
            self.set_status(ScraperStatus.RUNNING)
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            logger.info(f"Starting live scraping for {url} with {update_interval}s interval")
            
            while not self.should_stop():
                try:
                    # Scrape current data
                    current_data = await self.scrape_single(url)
                    
                    if current_data:
                        # Check if data has changed significantly
                        if self.has_significant_changes(current_data):
                            await self.emit_update(current_data)
                            logger.info("Emitted update due to significant changes")
                        else:
                            # Still emit periodic updates but mark as unchanged
                            await self.emit_update(current_data, status="unchanged")
                        
                        # Reset error counter on success
                        consecutive_errors = 0
                    else:
                        consecutive_errors += 1
                        logger.warning(f"Scrape returned no data (error {consecutive_errors}/{max_consecutive_errors})")
                    
                    # Check for too many consecutive errors
                    if consecutive_errors >= max_consecutive_errors:
                        raise Exception(f"Too many consecutive scraping failures ({consecutive_errors})")
                    
                    # Wait for next update
                    await self.safe_sleep(update_interval)
                    
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error in live scraping loop: {e}")
                    await self.emit_error(str(e), "live_scraping")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Maximum consecutive errors reached, stopping live scraping")
                        break
                    
                    # Wait longer after error
                    await self.safe_sleep(min(30.0, update_interval * 2))
            
        except Exception as e:
            logger.error(f"Fatal error in live scraping: {e}")
            await self.emit_error(f"Fatal live scraping error: {str(e)}", "fatal")
        finally:
            self.set_status(ScraperStatus.COMPLETED)
            logger.info("Live scraping completed")
    
    def has_significant_changes(self, new_data: Dict[str, Any]) -> bool:
        """
        Check if new data has significant changes compared to last results
        """
        if not self.last_results:
            return True
        
        try:
            # Compare division count
            old_divisions = self.last_results.get("divisions", [])
            new_divisions = new_data.get("divisions", [])
            
            if len(old_divisions) != len(new_divisions):
                return True
            
            # Compare each division
            for i, (old_div, new_div) in enumerate(zip(old_divisions, new_divisions)):
                # Check if results changed
                old_results = old_div.get("results", [])
                new_results = new_div.get("results", [])
                
                if len(old_results) != len(new_results):
                    return True
                
                # Check for position or points changes
                for old_result, new_result in zip(old_results, new_results):
                    if (old_result.get("position") != new_result.get("position") or
                        old_result.get("total_points") != new_result.get("total_points") or
                        old_result.get("race_results") != new_result.get("race_results")):
                        return True
                
                # Check last updated time
                if old_div.get("last_updated") != new_div.get("last_updated"):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error comparing data for changes: {e}")
            return True  # Assume changes if we can't compare
    
   # In RegattaNetworkScraper.emit_update method, replace the entire method with:
    async def emit_update(self, data: Dict[str, Any], status: str = "success"):
        """Override and emit regatta network specific update to connected clients"""
        try:
            if not self.socketio or not self.session_id:
                logger.error(f"Cannot emit regatta network update - missing socketio: {self.socketio is not None}, session_id: {self.session_id}")
                return
            
            await self.update_activity()
            
            # Add session metadata to the existing data structure instead of wrapping it
            enhanced_data = data.copy()
            enhanced_data['session_id'] = self.session_id
            enhanced_data['status'] = status
            enhanced_data['timestamp'] = datetime.now().isoformat()
            enhanced_data['source'] = self.scraper_type.value
            enhanced_data['scraper_mode'] = self.mode.value
            
            # Update metadata section with session info
            if 'metadata' not in enhanced_data:
                enhanced_data['metadata'] = {}
            enhanced_data['metadata'].update({
                'session_id': self.session_id,
                'status': status,
                'live_update': True,
                'scraper_source': self.scraper_type.value
            })
            
            logger.info(f"Emitting regatta_network_update for session {self.session_id} with {len(data.get('divisions', []))} divisions")
            
            # Emit the enhanced data directly (not wrapped in another object)
            await self.socketio.emit('regatta_network_update', enhanced_data, room=self.session_id)
            
            self.total_operations += 1
            logger.info(f"Successfully emitted regatta network update for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error emitting regatta network update: {e}")
            if self.socketio and self.session_id:
                try:
                    await self.socketio.emit('regatta_network_error', {
                        'session_id': self.session_id,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }, room=self.session_id)
                except Exception as emit_error:
                    logger.error(f"Failed to emit error event: {emit_error}")

# Register the scraper with the factory
ScraperFactory.register_scraper('regatta_network', RegattaNetworkScraper)