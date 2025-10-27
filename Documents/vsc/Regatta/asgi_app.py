from quart import Quart, request, jsonify
import socketio
import asyncio
import uuid
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
from base_scraper import ScraperFactory, ScraperMode, ScraperType

# CRITICAL: Import all scraper modules to ensure registration
# This must happen BEFORE any scraper factory usage
import main_scraper  # This triggers the registration
import api_scraper  
import regatta_network_scraper
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('regatta_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Verify scrapers are registered at startup
def verify_scrapers():
    """Verify that all expected scrapers are registered"""
    available = ScraperFactory.list_available_scrapers()
    expected = ['clubspot_main', 'clubspot_api', 'regatta_network']  # Add more as they're implemented
    
    logger.info(f"Available scrapers: {available}")
    
    missing = [scraper for scraper in expected if scraper not in available]
    if missing:
        logger.error(f"Missing scrapers: {missing}")
        raise RuntimeError(f"Required scrapers not registered: {missing}")
    
    logger.info("All required scrapers are registered successfully")

# Verify scrapers at module load
verify_scrapers()

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    cors_allowed_origins=[
        "https://app.regatta-results.com",
        "https://*.regatta-results.com"
    ],
    async_mode='asgi',
    logger=True,
    engineio_logger=True,
    transports=['websocket'],
    ping_timeout=60,
    ping_interval=25,
    always_connect=True,
    allow_upgrades=True,
    # Add these for SSL/Cloudflare compatibility
    ssl_verify=False,
    engineio_options={
        'ping_timeout': 60,
        'ping_interval': 25,
        'upgrade_timeout': 10,
        'close_timeout': 60
    }
)

# Global session management
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.cleanup_task = None
        self._cleanup_task_needed = False
        # Increased thread pool for better concurrency
        self.thread_pool = ThreadPoolExecutor(max_workers=20)
        self.start_cleanup_task()
    
    async def create_session(self, url: str, client_id: Optional[str] = None, 
                           scraper_type: str = 'clubspot_main', run_once: bool = False) -> str:
        """Create a new scraping session with modern scraper types"""
        session_id = str(uuid.uuid4())
        await self.ensure_cleanup_task_started()
        
        # Validate scraper type
        available_scrapers = ScraperFactory.list_available_scrapers()
        if scraper_type not in available_scrapers:
            raise ValueError(f"Unknown scraper type: {scraper_type}. Available: {available_scrapers}")
        
        async with self.lock:
            self.sessions[session_id] = {
                'url': url,
                'client_id': client_id,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'status': 'created',
                'task': None,
                'error_count': 0,
                'scraper_type': scraper_type,
                'stop_event': asyncio.Event(),
                'run_once': run_once,
                'scraper_instance': None
            }
        
        logger.info(f"Created session {session_id} for URL: {url} using {scraper_type} scraper")
        return session_id

    async def _run_main_scraper(self, url: str, session_id: str):
        """Run the main scraper in async mode"""
        scraper_instance = None
        try:
            # Create scraper instance
            scraper_instance = ScraperFactory.create_scraper('clubspot_main', ScraperMode.LIVE)
            scraper_instance.set_socketio_and_session_manager(sio, self)
            scraper_instance.set_session_context(session_id, self.sessions[session_id].get('stop_event'))
            
            # Store reference to scraper instance for stopping
            async with self.lock:
                if session_id in self.sessions:
                    self.sessions[session_id]['scraper_instance'] = scraper_instance
                    run_once = self.sessions[session_id].get('run_once', False)
                else:
                    return
            
            # Run the scraper
            mode = ScraperMode.SINGLE if run_once else ScraperMode.LIVE
            scraper_instance.mode = mode
            await scraper_instance.run(url, update_interval=20.0)
            
        except Exception as e:
            logger.error(f"Main scraper error for session {session_id}: {e}")
            await self._update_session_status(session_id, 'error')
        finally:
            # Clean up scraper reference
            async with self.lock:
                if session_id in self.sessions and 'scraper_instance' in self.sessions[session_id]:
                    del self.sessions[session_id]['scraper_instance']
            
            # Stop the scraper if it exists
            if scraper_instance:
                try:
                    await scraper_instance.stop()
                except Exception as e:
                    logger.warning(f"Error stopping scraper in finally block: {e}")
            
            await self._update_session_status(session_id, 'completed')

    async def _run_scraper(self, url: str, session_id: str):
        """Run any scraper type using the factory pattern"""
        scraper_instance = None
        try:
            # Get session info safely
            async with self.lock:
                if session_id not in self.sessions:
                    return
                session = self.sessions[session_id]
                scraper_type = session['scraper_type'] 
                run_once = session.get('run_once', False)
            
            # Create scraper instance using factory
            mode = ScraperMode.SINGLE if run_once else ScraperMode.LIVE
            scraper_instance = ScraperFactory.create_scraper(scraper_type, mode)
            scraper_instance.set_socketio_and_session_manager(sio, self)
            scraper_instance.set_session_context(session_id, self.sessions[session_id].get('stop_event'))
            
            logger.info(f"Scraper setup verification for {scraper_type}:")
            logger.info(f"  - Socketio set: {scraper_instance.socketio is not None}")
            logger.info(f"  - Session ID: {scraper_instance.session_id}")
            logger.info(f"  - Session manager: {scraper_instance.session_manager is not None}")

            # Verify the socketio instance has the emit method
            if scraper_instance.socketio:
                logger.info(f"  - Socketio has emit method: {hasattr(scraper_instance.socketio, 'emit')}")
            else:
                logger.error("  - CRITICAL: Socketio is None!")
            # Store reference to scraper instance for stopping
            async with self.lock:
                if session_id in self.sessions:
                    self.sessions[session_id]['scraper_instance'] = scraper_instance
                else:
                    return
            
            # Run the scraper
            await scraper_instance.run(url)
            
        except Exception as e:
            logger.error(f"scraper error for session {session_id}: {e}")
            await self._update_session_status(session_id, 'error')
        finally:
            # Clean up scraper reference
            async with self.lock:
                if session_id in self.sessions and 'scraper_instance' in self.sessions[session_id]:
                    del self.sessions[session_id]['scraper_instance']
            
            # Stop the scraper if it exists
            if scraper_instance:
                try:
                    await scraper_instance.stop()
                except Exception as e:
                    logger.warning(f"Error stopping scraper in finally block: {e}")
            
            await self._update_session_status(session_id, 'completed')
            
    async def _update_session_status(self, session_id: str, status: str):
        """Update session status"""
        async with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['status'] = status
                self.sessions[session_id]['last_activity'] = datetime.now()
    
    async def start_session(self, session_id: str) -> bool:
        """Start scraping for a session using unified scraper runner"""
        async with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            if session['status'] == 'running':
                return True
            
            # Create scraper task using unified runner
            task = asyncio.create_task(
                self._run_scraper(session['url'], session_id)
            )
            
            session['task'] = task
            session['status'] = 'running'
            session['last_activity'] = datetime.now()
            
        logger.info(f"Started {session['scraper_type']} scraping for session {session_id}")
        return True
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop scraping for a session"""
        async with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            
            # Set the stop event - this is the new unified way to stop all scrapers
            if 'stop_event' in session:
                session['stop_event'].set()
            
            session['status'] = 'stopping'
            
            # Cancel the task if it exists
            if session.get('task') and not session['task'].done():
                session['task'].cancel()
                try:
                    await session['task']
                except asyncio.CancelledError:
                    pass
            
            # If we have a reference to the scraper instance, call its stop method
            if hasattr(session, 'scraper_instance') and session['scraper_instance']:
                try:
                    await session['scraper_instance'].stop()
                except Exception as e:
                    logger.warning(f"Error stopping scraper instance: {e}")
        
        logger.info(f"Stopped scraping for session {session_id}")
        return True
    
    async def remove_session(self, session_id: str):
        """Remove a session completely"""
        async with self.lock:
            if session_id in self.sessions:
                await self.stop_session(session_id)
                await asyncio.sleep(1)
                del self.sessions[session_id]
                logger.info(f"Removed session {session_id}")
    
    async def update_activity(self, session_id: str):
        """Update last activity time for a session"""
        async with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['last_activity'] = datetime.now()
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        async with self.lock:
            session = self.sessions.get(session_id, {})
            # Create a copy without the task object for JSON serialization
            return {k: v for k, v in session.items() if k not in ['task', 'stop_event']}
    
    async def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions"""
        async with self.lock:
            return {sid: {
                'url': session['url'],
                'status': session['status'],
                'created_at': session['created_at'].isoformat(),
                'last_activity': session['last_activity'].isoformat(),
                'scraper_type': session['scraper_type'],
                'run_mode': 'once' if session.get('run_once', False) else 'continuous'
            } for sid, session in self.sessions.items()}

    async def cleanup_inactive_sessions(self):
        """Remove sessions that have been inactive for too long"""
        cutoff_time = datetime.now() - timedelta(minutes=30)  # 30 minute timeout
        to_remove = []
        
        async with self.lock:
            for session_id, session in self.sessions.items():
                if session['last_activity'] < cutoff_time:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            logger.info(f"Cleaning up inactive session: {session_id}")
            await self.remove_session(session_id)
    
    def start_cleanup_task(self):
        """Mark that cleanup task should be started - actual start happens later"""
        self.cleanup_task = None
        self._cleanup_task_needed = True

    async def ensure_cleanup_task_started(self):
        """Start cleanup task if not already started"""
        if self._cleanup_task_needed and (self.cleanup_task is None or self.cleanup_task.done()):
            async def cleanup_worker():
                while True:
                    try:
                        await self.cleanup_inactive_sessions()
                        await asyncio.sleep(300)  # Check every 5 minutes
                    except Exception as e:
                        logger.error(f"Cleanup task error: {e}")
                        await asyncio.sleep(60)
            
            self.cleanup_task = asyncio.create_task(cleanup_worker())
            self._cleanup_task_needed = False

# Initialize session manager
session_manager = SessionManager()

# Create Quart app for HTTP routes
quart_app = Quart(__name__)
quart_app.config['SECRET_KEY'] = 'sumans-key-quart-180825'

# API Routes
@quart_app.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "available_scrapers": ScraperFactory.list_available_scrapers(),
        "registered_scrapers": {
            "clubspot_main": "Event information scraper",
            "clubspot_api": "API discovery scraper", 
            "regatta_network": "Regatta Network results scraper"# Add others as they're migrated
        },
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"  # Update version
    })

@quart_app.route('/start', methods=['POST'])
async def start_scraping():
    """Start a new scraping session with the new architecture"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        client_id = data.get('client_id')
        scraper_type = data.get('scraper_type', 'clubspot_main')  # Default to main scraper
        run_once = data.get('run_once', False)
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Validate scraper type
        available_scrapers = ScraperFactory.list_available_scrapers()
        if scraper_type not in available_scrapers:
            return jsonify({
                "error": f"Unknown scraper type: {scraper_type}",
                "available_scrapers": available_scrapers
            }), 400
        
        logger.info(f"Starting {scraper_type} scraping for URL: {url} ({'once' if run_once else 'continuous'} mode)")
        
        # Create session with the specified scraper type
        session_id = await session_manager.create_session(
            url=url,
            client_id=client_id,
            scraper_type=scraper_type,
            run_once=run_once
        )
        
        # Start the scraping session
        if await session_manager.start_session(session_id):
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "url": url,
                "scraper_type": scraper_type,
                "run_mode": "once" if run_once else "continuous",
                "message": f"{scraper_type} scraping started ({'once' if run_once else 'continuous'} mode)"
            })
        else:
            await session_manager.remove_session(session_id)  # Clean up failed session
            return jsonify({
                "error": "Failed to start scraping session"
            }), 500
            
    except ValueError as e:
        # Handle scraper validation errors
        logger.error(f"Validation error starting scraping: {e}")
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@quart_app.route('/scrape-event-info', methods=['POST'])
async def scrape_event_info_http():
    """Scrape event information and return results directly via HTTP"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        logger.info(f"Starting direct HTTP event info scraping for URL: {url}")
        
        # Create a temporary scraper instance for this request
        scraper_instance = ScraperFactory.create_scraper('clubspot_main', ScraperMode.SINGLE)
        scraper_instance.set_socketio_and_session_manager(sio, session_manager)
        
        
        try:
            # Run the scraper directly and get results
            event_info = await scraper_instance.scrape_single(url)
            
            if event_info:
                response = {
                    "status": "success",
                    "event_data": event_info,
                    "message": "Event information scraped successfully"
                }
                logger.info(f"Event info scraping successful for URL: {url}")
                return jsonify(response)
            else:
                return jsonify({
                    "status": "error",
                    "error": "Failed to scrape event information",
                    "event_data": None
                }), 500
                
        except Exception as e:
            logger.error(f"Error in event info scraping: {e}")
            return jsonify({
                "status": "error", 
                "error": f"Scraping failed: {str(e)}",
                "event_data": None
            }), 500
            
    except Exception as e:
        logger.error(f"Error in scrape-event-info route: {e}")
        return jsonify({
            "status": "error", 
            "error": "Internal server error",
            "event_data": None
        }), 500

@quart_app.route('/discover-only', methods=['POST'])
async def discover_only():
    """Discover API URLs and return them directly without starting continuous scraping"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        logger.info(f"Starting API discovery for URL: {url}")
        
        # Check if clubspot_api scraper is available
        available_scrapers = ScraperFactory.list_available_scrapers()
        if 'clubspot_api' not in available_scrapers:
            return jsonify({
                "status": "error",
                "error": "API discovery scraper not available",
                "api_urls": {},
                "combinations": []
            }), 501
        
        # Create a temporary scraper instance for discovery
        discovery_scraper = ScraperFactory.create_scraper('clubspot_api', ScraperMode.SINGLE)
        discovery_scraper.set_socketio_and_session_manager(sio, session_manager)
        
        try:
            # Run the discovery
            result = await discovery_scraper.scrape_single(url)
            
            if result:
                response = {
                    "status": "success",
                    "api_urls": result["api_urls"],
                    "combinations": result["combinations"],
                    "message": f"Discovered {result['metadata']['total_urls']} API URLs with {result['metadata']['total_combinations']} dropdown combinations"
                }
                
                logger.info(f"API discovery successful: {result['metadata']['total_urls']} URLs found")
                return jsonify(response)
            else:
                raise Exception("Discovery returned no results")
                
        except Exception as e:
            logger.error(f"Error in discovery: {e}")
            return jsonify({
                "status": "error", 
                "error": f"Discovery failed: {str(e)}",
                "api_urls": {},
                "combinations": []
            }), 500
            
    except Exception as e:
        logger.error(f"Error in discover-only route: {e}")
        return jsonify({
            "status": "error", 
            "error": "Internal server error",
            "api_urls": {},
            "combinations": []
        }), 500

@quart_app.route('/scrape-regatta-network', methods=['POST'])
async def scrape_regatta_results():
    """Scrape Regatta Network results and return data directly via HTTP"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Validate URL format
        if "regattanetwork.com" not in url:
            return jsonify({"error": "URL must be from regattanetwork.com"}), 400
        
        logger.info(f"Starting regatta results scraping for URL: {url}")
        
        # Create a temporary scraper instance for this request
        scraper_instance = ScraperFactory.create_scraper('regatta_network', ScraperMode.SINGLE)
        scraper_instance.set_socketio_and_session_manager(sio, session_manager)
        
        try:
            # Run the scraper directly and get results
            regatta_data = await scraper_instance.scrape_single(url)
            
            if regatta_data:
                response = {
                    "status": "success",
                    "regatta_data": regatta_data,
                    "message": "Regatta results scraped successfully"
                }
                logger.info(f"Regatta results scraping successful for URL: {url}")
                return jsonify(response)
            else:
                return jsonify({
                    "status": "error",
                    "error": "Failed to scrape regatta results",
                    "regatta_data": None
                }), 500
                
        except Exception as e:
            logger.error(f"Error in regatta results scraping: {e}")
            return jsonify({
                "status": "error", 
                "error": f"Scraping failed: {str(e)}",
                "regatta_data": None
            }), 500
            
    except Exception as e:
        logger.error(f"Error in scrape-regatta-results route: {e}")
        return jsonify({
            "status": "error", 
            "error": "Internal server error",
            "regatta_data": None
        }), 500

@quart_app.route('/stop', methods=['POST'])
async def stop_scraping():
    """Stop a scraping session"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        # Get session info before stopping for response details
        session_info = await session_manager.get_session_info(session_id)
        if not session_info:
            return jsonify({"error": "Session not found"}), 404
        
        scraper_type = session_info.get('scraper_type', 'unknown')
        
        logger.info(f"Stopping {scraper_type} scraping for session: {session_id}")
        
        # Start the stop process asynchronously - don't wait for completion
        asyncio.create_task(session_manager.stop_session(session_id))
        
        # Respond immediately
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "scraper_type": scraper_type,
            "message": f"{scraper_type} scraping stop initiated"
        })
            
    except Exception as e:
        logger.error(f"Error stopping scraping: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Optional: Add a /stop-all endpoint for debugging/admin use
@quart_app.route('/stop-all', methods=['POST'])
async def stop_all_scraping():
    """Stop all active scraping sessions (admin/debug endpoint)"""
    try:
        active_sessions = await session_manager.list_active_sessions()
        stopped_count = 0
        errors = []
        
        for session_id in active_sessions.keys():
            try:
                if await session_manager.stop_session(session_id):
                    stopped_count += 1
                    logger.info(f"Stopped session: {session_id}")
                else:
                    errors.append(f"Failed to stop session: {session_id}")
            except Exception as e:
                errors.append(f"Error stopping session {session_id}: {str(e)}")
        
        return jsonify({
            "status": "success",
            "stopped_sessions": stopped_count,
            "total_sessions": len(active_sessions),
            "errors": errors,
            "message": f"Stopped {stopped_count}/{len(active_sessions)} sessions"
        })
        
    except Exception as e:
        logger.error(f"Error stopping all scraping sessions: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@quart_app.route('/status/<session_id>', methods=['GET'])
async def get_session_status(session_id):
    """Get status of a specific session"""
    try:
        session_info = await session_manager.get_session_info(session_id)
        
        if not session_info:
            return jsonify({"error": "Session not found"}), 404
        
        # Update activity since client is checking status
        await session_manager.update_activity(session_id)
        
        return jsonify({
            "session_id": session_id,
            "status": session_info.get('status', 'unknown'),
            "url": session_info.get('url'),
            "scraper_type": session_info.get('scraper_type'),
            "run_mode": 'once' if session_info.get('run_once', False) else 'continuous',
            "created_at": session_info.get('created_at', datetime.now()).isoformat(),
            "last_activity": session_info.get('last_activity', datetime.now()).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@quart_app.route('/sessions', methods=['GET'])
async def list_sessions():
    """List all active sessions (for monitoring/debugging)"""
    try:
        return jsonify({
            "active_sessions": await session_manager.list_active_sessions(),
            "total_count": len(session_manager.sessions)
        })
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({"error": "Internal server error"}), 500

# WebSocket Events
@sio.event
def connect(sid, environ):
    logger.info(f"[SOCKET] Client connected: {sid} (environ: {environ.get('REMOTE_ADDR', 'unknown')})")
    return True

@sio.event
def disconnect(sid):
    logger.info(f"[SOCKET] Client disconnected: {sid}")

@sio.event
def connect_error(sid, data):
    logger.error(f"[SOCKET] Connection error for {sid}: {data}")

@sio.event
async def join_session(sid, data):
    """Handle client joining a specific session room"""
    try:
        session_id = data.get('session_id')
        if session_id and session_id in session_manager.sessions:
            await sio.enter_room(sid, session_id)
            await session_manager.update_activity(session_id)
            logger.info(f"Client {sid} joined session {session_id}")
            
            await sio.emit('joined_session', {
                'session_id': session_id,
                'status': 'success'
            }, room=sid)
        else:
            await sio.emit('error', {'message': 'Invalid session_id'}, room=sid)
    except Exception as e:
        logger.error(f"Error joining session: {e}")
        await sio.emit('error', {'message': 'Failed to join session'}, room=sid)

@sio.event
async def leave_session(sid, data):
    """Handle client leaving a session room"""
    try:
        session_id = data.get('session_id')
        if session_id:
            await sio.leave_room(sid, session_id)
            logger.info(f"Client {sid} left session {session_id}")
            
            await sio.emit('left_session', {
                'session_id': session_id,
                'status': 'success'
            }, room=sid)
    except Exception as e:
        logger.error(f"Error leaving session: {e}")
        await sio.emit('error', {'message': 'Failed to leave session'}, room=sid)

# Custom error handlers
@quart_app.errorhandler(404)
async def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@quart_app.errorhandler(500)
async def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Create the ASGI app
app = socketio.ASGIApp(sio, quart_app)

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🏁 Starting Regatta Results Scraper Server (ASGI)")
    logger.info("=" * 50)
    logger.info("Server will be available at: https://app.regatta-results.com")
    logger.info("Local server running on: http://0.0.0.0:5000")
    logger.info("=" * 50)
    
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5000,
        # Add these for better Cloudflare compatibility
        access_log=True,
        ws_ping_interval=25,
        ws_ping_timeout=60
    )