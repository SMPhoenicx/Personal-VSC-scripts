from abc import ABC, abstractmethod
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class ScraperType(Enum):
    """Enum for different scraper types"""
    API = "api"
    HTML = "html"
    HYBRID = "hybrid"

class ScraperMode(Enum):
    """Enum for scraper operation modes"""
    SINGLE = "single"
    LIVE = "live"

class ScraperStatus(Enum):
    """Enum for scraper status states"""
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

class BaseScraper(ABC):
    """
    Abstract base class for all scrapers providing:
    - Standard interface for all scrapers
    - Common connection handling
    - Unified error handling
    - Session management integration
    """
    
    def __init__(self, scraper_type: ScraperType, mode: ScraperMode = ScraperMode.SINGLE):
        self.scraper_type = scraper_type
        self.mode = mode
        self.status = ScraperStatus.CREATED
        self.session_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        self.error_count = 0
        self.total_operations = 0
        
        # SocketIO and session manager references
        self.socketio = None
        self.session_manager = None
        
        # Stop event for graceful shutdown
        self.stop_event: Optional[asyncio.Event] = None
        
        # Common headers for HTTP requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def set_socketio_and_session_manager(self, socket_instance, session_mgr):
        """Set SocketIO and session manager references"""
        self.socketio = socket_instance
        self.session_manager = session_mgr
    
    def set_session_context(self, session_id: str, stop_event: Optional[asyncio.Event] = None):
        """Set session context for this scraper instance"""
        self.session_id = session_id
        self.stop_event = stop_event
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.status = ScraperStatus.RUNNING
    
    async def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        if self.session_manager and self.session_id:
            await self.session_manager.update_activity(self.session_id)
    
    async def emit_update(self, data: Dict[str, Any], status: str = "success"):
        """Emit scraper update to connected clients"""
        try:
            if not self.socketio or not self.session_id:
                logger.warning("Cannot emit update - missing socketio or session_id")
                return
            
            await self.update_activity()
            
            await self.socketio.emit('scraper_update', {
                'session_id': self.session_id,
                'data': data,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'source': self.scraper_type.value,
                'scraper_mode': self.mode.value
            }, room=self.session_id)
            
            self.total_operations += 1
            logger.info(f"Emitted update for session {self.session_id} ({self.scraper_type.value})")
            
        except Exception as e:
            logger.error(f"Error emitting update: {e}")
    
    async def emit_error(self, error_message: str, error_type: str = "general"):
        """Emit scraper error to connected clients"""
        try:
            if not self.socketio or not self.session_id:
                logger.warning("Cannot emit error - missing socketio or session_id")
                return
            
            self.error_count += 1
            self.status = ScraperStatus.ERROR
            
            await self.socketio.emit('scraper_error', {
                'session_id': self.session_id,
                'error': error_message,
                'error_type': error_type,
                'timestamp': datetime.now().isoformat(),
                'source': self.scraper_type.value,
                'scraper_mode': self.mode.value
            }, room=self.session_id)
            
            logger.error(f"Emitted error for session {self.session_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error emitting error message: {e}")
    
    def should_stop(self) -> bool:
        """Check if scraper should stop based on stop event or status"""
        if self.stop_event is not None and self.stop_event.is_set():
            return True
        if self.status in [ScraperStatus.STOPPING, ScraperStatus.STOPPED]:
            return True
        return False
    
    async def safe_sleep(self, duration: float, check_interval: float = 0.1):
        """Sleep with periodic stop checks"""
        elapsed = 0.0
        while elapsed < duration and not self.should_stop():
            sleep_time = min(check_interval, duration - elapsed)
            await asyncio.sleep(sleep_time)
            elapsed += sleep_time
    
    def set_status(self, status: ScraperStatus):
        """Update scraper status"""
        self.status = status
        logger.info(f"Scraper {self.session_id} status changed to: {status.value}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        runtime = None
        if self.start_time:
            runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'scraper_type': self.scraper_type.value,
            'mode': self.mode.value,
            'status': self.status.value,
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'runtime_seconds': runtime,
            'error_count': self.error_count,
            'total_operations': self.total_operations
        }
    
    @abstractmethod
    async def discover(self, url: str) -> bool:
        """
        Discovery phase - find available data sources/endpoints
        Returns True if discovery was successful
        """
        pass
    
    @abstractmethod
    async def scrape_single(self, url: str) -> Dict[str, Any]:
        """
        Single scrape operation - get data once and return
        Returns scraped data or raises exception
        """
        pass
    
    async def scrape_live(self, url: str, update_interval: float = 10.0):
        """
        Live scraping operation - continuous scraping with updates
        Default implementation calls scrape_single in a loop
        Subclasses can override for more efficient live scraping
        """
        try:
            self.set_status(ScraperStatus.RUNNING)
            
            while not self.should_stop():
                try:
                    data = await self.scrape_single(url)
                    if data:
                        await self.emit_update(data)
                        self.error_count = 0  # Reset error count on success
                    else:
                        self.error_count += 1
                        if self.error_count >= 3:
                            raise Exception("Multiple failed scrape attempts")
                    
                    await self.safe_sleep(update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in live scraping loop: {e}")
                    await self.emit_error(str(e), "scraping_loop")
                    await self.safe_sleep(5.0)  # Wait longer after error
            
        except Exception as e:
            logger.error(f"Fatal error in live scraping: {e}")
            await self.emit_error(f"Fatal error: {str(e)}", "fatal")
        finally:
            self.set_status(ScraperStatus.COMPLETED)
    
    async def run(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Main entry point - runs scraper based on mode
        """
        try:
            logger.info(f"Starting {self.scraper_type.value} scraper in {self.mode.value} mode for URL: {url}")
            
            if self.mode == ScraperMode.SINGLE:
                return await self.scrape_single(url)
            elif self.mode == ScraperMode.LIVE:
                await self.scrape_live(url, kwargs.get('update_interval', 10.0))
                return None
            else:
                raise ValueError(f"Unsupported scraper mode: {self.mode}")
                
        except Exception as e:
            logger.error(f"Error in scraper run: {e}")
            await self.emit_error(str(e), "runtime")
            raise
    
    async def stop(self):
        """Stop the scraper gracefully"""
        logger.info(f"Stopping scraper {self.session_id}")
        self.set_status(ScraperStatus.STOPPING)
        if self.stop_event:
            self.stop_event.set()
    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'session_id') and self.session_id:
            logger.debug(f"Destroying scraper instance for session {self.session_id}")


class ScraperFactory:
    """Factory for creating scraper instances"""
    
    _scrapers = {}
    
    @classmethod
    def register_scraper(cls, name: str, scraper_class):
        """Register a scraper class"""
        cls._scrapers[name] = scraper_class
    
    @classmethod
    def create_scraper(cls, scraper_name: str, mode: ScraperMode = ScraperMode.SINGLE) -> BaseScraper:
        """Create a scraper instance"""
        if scraper_name not in cls._scrapers:
            raise ValueError(f"Unknown scraper type: {scraper_name}")
        
        scraper_class = cls._scrapers[scraper_name]
        return scraper_class(mode)
    
    @classmethod
    def list_available_scrapers(cls) -> List[str]:
        """List all registered scrapers"""
        return list(cls._scrapers.keys())


# Connection management utilities
class ConnectionManager:
    """Manages connection health and resilience"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def with_retries(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation failed after {self.max_retries} attempts: {e}")
        
        if last_exception:
            raise last_exception
        else:
            raise Exception("Operation failed after all retries")