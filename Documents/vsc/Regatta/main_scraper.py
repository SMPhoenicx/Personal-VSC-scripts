from playwright.async_api import async_playwright
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import re
from urllib.parse import urljoin, urlparse
from base_scraper import BaseScraper, ScraperType, ScraperMode, ScraperFactory

logger = logging.getLogger(__name__)

class ClubSpotMainScraper(BaseScraper):
    """
    ClubSpot main page scraper - extracts event information from event pages
    Optimized for single-use operations, inherits from BaseScraper for consistency
    """
    
    def __init__(self, mode: ScraperMode = ScraperMode.SINGLE):
        super().__init__(ScraperType.HTML, mode)
        
        # Browser management
        self.browser = None
        self.page = None
        
        # Performance optimization flags
        self._browser_reuse = False  # For future live mode optimization
        
    async def discover(self, url: str) -> bool:
        """
        Discovery phase - validate that this is a valid ClubSpot event page
        Returns True if URL is a valid ClubSpot event page
        """
        try:
            await self.update_activity()
            
            # Basic URL validation
            parsed_url = urlparse(url)
            if 'clubspot.com' not in parsed_url.netloc:
                logger.warning(f"URL does not appear to be a ClubSpot URL: {url}")
                return False
            
            # Quick page check
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    
                    # Check for ClubSpot-specific elements
                    event_page_indicator = await page.query_selector('.event-page-name, .event-card-image-inner-contain, .eventDateInsert')
                    
                    await browser.close()
                    
                    if event_page_indicator:
                        logger.info(f"Successfully discovered ClubSpot event page: {url}")
                        return True
                    else:
                        logger.warning(f"URL does not appear to be a ClubSpot event page: {url}")
                        return False
                        
                except Exception as e:
                    await browser.close()
                    logger.error(f"Error during discovery: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return False
    
    async def scrape_single(self, url: str) -> Dict[str, Any]:
        """
        Single scrape operation - extract event information once
        This is the main method used by scrape_event_info_direct
        """
        try:
            await self.update_activity()
            logger.info(f"Starting single scrape for URL: {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set headers for better compatibility
                await page.set_extra_http_headers(self.headers)
                
                try:
                    # Navigate to the main page with timeout
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # Extract event information
                    event_info = await self._extract_event_info(page)
                    
                    # Format the data
                    formatted_data = self._format_event_data(event_info, url)
                    
                    logger.info(f"Successfully scraped event info for: {url}")
                    return formatted_data
                    
                except Exception as e:
                    logger.error(f"Error during page scraping: {e}")
                    raise e
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Error in single scrape: {e}")
            await self.emit_error(f"Failed to scrape event info: {str(e)}", "scraping")
            raise e
    
    async def scrape_live(self, url: str, update_interval: float = 30.0):
        """
        Live scraping operation - continuous monitoring of event page
        Optimized for longer intervals since event info doesn't change frequently
        """
        try:
            self.set_status(self.status.RUNNING)
            logger.info(f"Starting live scraping for URL: {url} with {update_interval}s interval")
            
            # For live mode, we could optimize by keeping browser open
            # But for now, use the base implementation which calls scrape_single
            await super().scrape_live(url, update_interval)
            
        except Exception as e:
            logger.error(f"Error in live scraping: {e}")
            await self.emit_error(f"Live scraping failed: {str(e)}", "live_scraping")
            raise e
    
    async def _extract_event_info(self, page) -> Dict[str, Any]:
        """
        Extract event information from the main page
        Optimized version with better error handling and performance
        """
        try:
            event_info = {}
            
            # Parallel extraction for better performance
            extraction_tasks = [
                self._extract_image(page),
                self._extract_date(page),
                self._extract_location(page),
                self._extract_urls(page),
                self._extract_title(page),
                self._extract_description(page),
                self._extract_regatta_id(page)
            ]
            
            # Execute extractions in parallel
            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Extraction task {i} failed: {result}")
                elif isinstance(result, dict):
                    event_info.update(result)
                else:
                    logger.warning(f"Extraction task {i} returned unexpected type: {type(result)}")
            
            # PDF extraction is separate due to its complexity
            try:
                pdf_documents = await self._extract_pdf_documents(page)
                event_info['pdf_documents'] = pdf_documents
                logger.info(f"Successfully extracted {len(pdf_documents)} PDF documents")
            except Exception as e:
                logger.error(f"Error extracting PDF documents: {e}")
                event_info['pdf_documents'] = []
            
            return event_info
            
        except Exception as e:
            logger.error(f"Error extracting event info: {e}")
            return {}
    
    async def _extract_image(self, page) -> Dict[str, Any]:
        """Extract event image URL"""
        try:
            # Try natural-image first
            image_element = await page.query_selector('img.natural-image')
            if image_element:
                image_url = await image_element.get_attribute('src')
                return {'image_url': image_url}
            
            # Fallback: background-image style
            bg_element = await page.query_selector('.event-card-image-inner-contain')
            if bg_element:
                style = await bg_element.get_attribute('style')
                if style:
                    match = re.search(r'background-image: url\("([^"]+)"\)', style)
                    if match:
                        return {'image_url': match.group(1)}
            
            return {'image_url': None}
            
        except Exception as e:
            logger.warning(f"Could not extract image: {e}")
            return {'image_url': None}
    
    async def _extract_date(self, page) -> Dict[str, Any]:
        """Extract event date"""
        try:
            date_element = await page.query_selector('.eventDateInsert')
            if date_element:
                date_text = await date_element.text_content()
                return {'date': date_text.strip() if date_text else None}
            
            return {'date': None}
            
        except Exception as e:
            logger.warning(f"Could not extract date: {e}")
            return {'date': None}
    
    async def _extract_location(self, page) -> Dict[str, Any]:
        """Extract event location"""
        try:
            location_elements = await page.query_selector_all('.flexNoWrap.modern.leftText.tinyMarginLeft')
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            for element in location_elements:
                text = await element.text_content()
                if text and text.strip():
                    first_word = text.strip().split()[0]
                    if first_word not in months:  # Not a date
                        return {'location': text.strip()}
            
            return {'location': None}
            
        except Exception as e:
            logger.warning(f"Could not extract location: {e}")
            return {'location': None}
    
    async def _extract_urls(self, page) -> Dict[str, Any]:
        """Extract results and registration URLs"""
        try:
            urls = {}
            base_url = page.url
            
            # Results URL
            results_button = await page.query_selector('a[href*="/results"]')
            if results_button:
                results_href = await results_button.get_attribute('href')
                if results_href:
                    urls['results_url'] = urljoin(base_url, results_href)
            else:
                urls['results_url'] = None
            
            # Registration URL
            register_button = await page.query_selector('a[href*="/register"]')
            if register_button:
                register_href = await register_button.get_attribute('href')
                if register_href:
                    urls['register_url'] = urljoin(base_url, register_href)
            else:
                urls['register_url'] = None
            
            return urls
            
        except Exception as e:
            logger.warning(f"Could not extract URLs: {e}")
            return {'results_url': None, 'register_url': None}
    
    async def _extract_title(self, page) -> Dict[str, Any]:
        """Extract event title"""
        try:
            title_element = await page.query_selector('.event-page-name')
            if title_element:
                title_text = await title_element.text_content()
                return {'title': title_text.strip() if title_text else None}
            
            # Fallback: page title
            page_title = await page.title()
            return {'title': page_title}
            
        except Exception as e:
            logger.warning(f"Could not extract title: {e}")
            return {'title': None}
    
    async def _extract_description(self, page) -> Dict[str, Any]:
        """Extract event description"""
        try:
            desc_element = await page.query_selector('.event-description, .regatta-description, .event-details')
            if desc_element:
                desc_text = await desc_element.text_content()
                return {'description': desc_text.strip() if desc_text else None}
            
            return {'description': None}
            
        except Exception as e:
            logger.warning(f"Could not extract description: {e}")
            return {'description': None}
    
    async def _extract_regatta_id(self, page) -> Dict[str, Any]:
        """Extract regatta ID from URL"""
        try:
            url_parts = urlparse(page.url)
            path_parts = url_parts.path.split('/')
            if 'regatta' in path_parts:
                regatta_index = path_parts.index('regatta')
                if regatta_index + 1 < len(path_parts):
                    return {'regatta_id': path_parts[regatta_index + 1]}
            
            return {'regatta_id': None}
            
        except Exception as e:
            logger.warning(f"Could not extract regatta ID: {e}")
            return {'regatta_id': None}
    
    async def _extract_pdf_documents(self, page) -> list:
        """
        Extract PDF document URLs - optimized version
        Uses window.open override to capture PDF URLs when documents are clicked
        """
        try:
            pdf_documents = []
            document_rows = await page.query_selector_all('.documentRow')
            
            if not document_rows:
                logger.info("No document rows found")
                return []
            
            logger.info(f"Found {len(document_rows)} document rows")
            
            # Set up window.open override to capture URLs
            await page.evaluate("""
                () => {
                    window._originalOpen = window.open;
                    window._capturedUrls = [];
                    
                    window.open = function(url, target, features) {
                        console.log('Captured PDF URL:', url);
                        window._capturedUrls.push(url);
                        return {
                            close: () => {},
                            focus: () => {},
                            location: { href: url },
                            document: { title: 'Document' }
                        };
                    };
                }
            """)
            
            # Process each document row with improved error handling
            for i, row in enumerate(document_rows):
                try:
                    # Extract document metadata
                    doc_info = await self._extract_document_info(row, i)
                    
                    # Get URLs before clicking
                    urls_before = await page.evaluate("() => window._capturedUrls.length")
                    
                    # Try to trigger URL capture
                    await self._trigger_document_click(row, doc_info['name'])
                    
                    # Wait for potential async operations
                    await page.wait_for_timeout(300)
                    
                    # Check for captured URL
                    pdf_url = await self._get_captured_url(page, urls_before, doc_info['name'])
                    
                    # If no URL captured, try alternative methods
                    if not pdf_url:
                        pdf_url = await self._try_alternative_url_extraction(page, row, doc_info['name'])
                    
                    doc_info['url'] = pdf_url
                    pdf_documents.append(doc_info)
                    
                    logger.info(f"Document processed: {doc_info['name']} -> {pdf_url or 'No URL'}")
                    
                except Exception as row_error:
                    logger.error(f"Error processing document row {i}: {row_error}")
                    # Add document with error info
                    pdf_documents.append({
                        'name': f"Document {i+1}",
                        'upload_date': None,
                        'url': None,
                        'error': str(row_error)
                    })
            
            # Restore original window.open
            await page.evaluate("""
                () => {
                    if (window._originalOpen) {
                        window.open = window._originalOpen;
                        delete window._originalOpen;
                        delete window._capturedUrls;
                    }
                }
            """)
            
            successful_extractions = len([doc for doc in pdf_documents if doc.get('url')])
            logger.info(f"Extracted {successful_extractions}/{len(pdf_documents)} PDF URLs")
            return pdf_documents
            
        except Exception as e:
            logger.error(f"Error in _extract_pdf_documents: {e}")
            return []
    
    async def _extract_document_info(self, row, index: int) -> Dict[str, Any]:
        """Extract basic document information from row"""
        try:
            # Document name
            name_element = await row.query_selector('td:first-child p')
            doc_name = await name_element.text_content() if name_element else f"Document {index+1}"
            
            # Upload date
            date_element = await row.query_selector('td:last-child p')
            upload_date = await date_element.text_content() if date_element else None
            
            return {
                'name': doc_name.strip(),
                'upload_date': upload_date.strip() if upload_date else None
            }
        except Exception as e:
            logger.warning(f"Error extracting document info: {e}")
            return {
                'name': f"Document {index+1}",
                'upload_date': None
            }
    
    async def _trigger_document_click(self, row, doc_name: str):
        """Try different methods to trigger document URL capture"""
        try:
            # Method 1: Click the view button
            view_button = await row.query_selector('button:has-text("view document")')
            if view_button:
                await view_button.click()
                return
        except Exception:
            pass
        
        try:
            # Method 2: Click the row itself
            await row.click()
        except Exception as e:
            logger.warning(f"Failed to click document row for {doc_name}: {e}")
    
    async def _get_captured_url(self, page, urls_before: int, doc_name: str) -> Optional[str]:
        """Check if a new URL was captured"""
        try:
            captured_info = await page.evaluate("""
                (urlsBefore) => {
                    const currentUrls = window._capturedUrls;
                    if (currentUrls.length > urlsBefore) {
                        return currentUrls[currentUrls.length - 1];
                    }
                    return null;
                }
            """, urls_before)
            
            if captured_info:
                logger.info(f"Successfully captured URL for {doc_name}")
                return captured_info
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting captured URL for {doc_name}: {e}")
            return None
    
    async def _try_alternative_url_extraction(self, page, row, doc_name: str) -> Optional[str]:
        """Try alternative methods to extract PDF URL"""
        try:
            # Try to get document ID from row class
            row_class = await row.get_attribute('class')
            doc_id = None
            
            if row_class:
                match = re.search(r'documentRow_([A-Za-z0-9]+)', row_class)
                if match:
                    doc_id = match.group(1)
            
            if doc_id:
                # Try direct URL construction based on common patterns
                alternative_url = await page.evaluate("""
                    (docId) => {
                        try {
                            // Check for document data in common locations
                            const sources = [window.documents, window.documentData, window.fileData];
                            
                            for (let source of sources) {
                                if (source && source[docId]) {
                                    const docObj = source[docId];
                                    if (docObj && typeof docObj.get === 'function') {
                                        return docObj.get('URL');
                                    }
                                    if (docObj && (docObj.URL || docObj.url)) {
                                        return docObj.URL || docObj.url;
                                    }
                                }
                            }
                            
                            // Try CloudFront pattern (common for ClubSpot)
                            return 'https://d282wvk2qi4wzk.cloudfront.net/' + docId + '.pdf';
                            
                        } catch (error) {
                            return null;
                        }
                    }
                """, doc_id)
                
                if alternative_url:
                    logger.info(f"Alternative URL extraction successful for {doc_name}")
                    return alternative_url
            
            return None
            
        except Exception as e:
            logger.warning(f"Alternative URL extraction failed for {doc_name}: {e}")
            return None
    
    def _format_event_data(self, event_info: Dict[str, Any], original_url: str) -> Dict[str, Any]:
        """Format event data for client consumption"""
        return {
            "event_info": {
                "title": event_info.get('title'),
                "date": event_info.get('date'),
                "location": event_info.get('location'),
                "image_url": event_info.get('image_url'),
                "results_url": event_info.get('results_url'),
                "register_url": event_info.get('register_url'),
                "description": event_info.get('description'),
                "regatta_id": event_info.get('regatta_id'),
                "pdf_documents": event_info.get('pdf_documents', []),
                "original_url": original_url
            },
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "source": "main_page",
                "scraper_version": "2.0.0",
                "scraper_type": self.scraper_type.value,
                "mode": self.mode.value
            }
        }
    
    async def stop(self):
        """Stop the scraper gracefully"""
        await super().stop()
        
        # Clean up browser resources if needed
        if self.browser:
            try:
                self.browser.close()
                self.browser = None
                self.page = None
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")


# Register the scraper with the factory
ScraperFactory.register_scraper('clubspot_main', ClubSpotMainScraper)

# Legacy compatibility functions for existing code
async def scrape_event_info_direct(url: str) -> Dict[str, Any]:
    """
    Legacy compatibility function - creates a scraper instance and runs it
    This maintains backward compatibility with existing HTTP route
    """
    scraper = ClubSpotMainScraper(ScraperMode.SINGLE)
    return await scraper.scrape_single(url)

# Global variables for backward compatibility (to be removed in Phase 4)
socketio = None
session_manager = None
main_scraper_statuses = {}

def set_socketio_and_session_manager(socket_instance, session_mgr):
    """Legacy compatibility function"""
    global socketio, session_manager
    socketio = socket_instance
    session_manager = session_mgr

def stop_main_scraping(session_id: str):
    """Legacy compatibility function"""
    if session_id in main_scraper_statuses:
        main_scraper_statuses[session_id]['running'] = False
        logger.info(f"Stop signal sent to main scraping session {session_id}")