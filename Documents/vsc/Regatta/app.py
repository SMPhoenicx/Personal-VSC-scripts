from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import uuid
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import scraper
import api_scraper
import asyncio
import main_scraper
from concurrent.futures import ThreadPoolExecutor

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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
# Changed to threading mode for better Playwright compatibility
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global session management
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.cleanup_thread = None
        self.api_scraper = api_scraper.ClubSpotAPIScraper()
        self.main_scraper = main_scraper.ClubSpotMainScraper()
        # Reduced thread pool size for better resource management
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.start_cleanup_thread()
    
    def create_session(self, url: str, client_id: str = None, use_api: bool = True, use_main: bool = True, run_once: bool = False) -> str:
        """Create a new scraping session"""
        session_id = str(uuid.uuid4())
        
        with self.lock:
            self.sessions[session_id] = {
                'url': url,
                'client_id': client_id,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'status': 'created',
                'thread': None,
                'error_count': 0,
                'scraper_type': 'main' if use_main else 'api' if use_api else 'html',
                'stop_event': threading.Event(), 
                'run_once': run_once
            }
        
        logger.info(f"Created session {session_id} for URL: {url} using {'main' if use_main else 'api' if use_api else 'html'} scraper")
        return session_id
    
    def _run_api_scraper_thread(self, url: str, session_id: str):
        """Run the API scraper in a dedicated thread with its own event loop"""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a new scraper instance and set its references
            scraper_instance = api_scraper.ClubSpotAPIScraper()
            scraper_instance.set_socketio_and_session_manager(socketio, self)
            
            # Pass the stop event to the scraper
            stop_event = self.sessions[session_id]['stop_event']
            run_once = self.sessions[session_id].get('run_once', False)  # Add this line
            
            # Run the async scraper
            loop.run_until_complete(
                scraper_instance.start_scraping(url, session_id, stop_event, run_once=run_once)  # Add run_once parameter
            )
            
        except Exception as e:
            logger.error(f"API scraper error for session {session_id}: {e}")
            self._update_session_status(session_id, 'error')
        finally:
            # Clean up the event loop
            try:
                loop.close()
            except:
                pass
            # If run_once is True, mark as completed instead of stopped
            status = 'completed' if self.sessions[session_id].get('run_once', False) else 'stopped'
            self._update_session_status(session_id, status)

    def _run_main_scraper_thread(self, url: str, session_id: str):
        """Run the main scraper in a dedicated thread with its own event loop"""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a new scraper instance and set its references
            scraper_instance = main_scraper.ClubSpotMainScraper()
            scraper_instance.set_socketio_and_session_manager(socketio, self)
            
            run_once = self.sessions[session_id].get('run_once', False)  # Add this line
            
            # Run the async scraper
            if run_once:
                # For run_once, just scrape once and finish
                loop.run_until_complete(
                    scraper_instance.scrape_event_info(url, session_id)
                )
            else:
                # For continuous mode, use existing logic
                loop.run_until_complete(
                    scraper_instance.scrape_event_info(url, session_id)
                )
            
        except Exception as e:
            logger.error(f"Main scraper error for session {session_id}: {e}")
            self._update_session_status(session_id, 'error')
        finally:
            # Clean up the event loop
            try:
                loop.close()
            except:
                pass
            self._update_session_status(session_id, 'completed')

    def _run_html_scraper_thread(self, url: str, session_id: str):
        """Run the HTML scraper in a dedicated thread"""
        try:
            stop_event = self.sessions[session_id]['stop_event']
            run_once = self.sessions[session_id].get('run_once', False)  # Add this line
            scraper.start_scraping_with_updates(url, session_id, stop_event, run_once=run_once)  # Add run_once parameter
        except Exception as e:
            logger.error(f"HTML scraper error for session {session_id}: {e}")
            self._update_session_status(session_id, 'error')
        finally:
            status = 'completed' if self.sessions[session_id].get('run_once', False) else 'stopped'
            self._update_session_status(session_id, status)
    def _update_session_status(self, session_id: str, status: str):
        """Thread-safe status update"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['status'] = status
                self.sessions[session_id]['last_activity'] = datetime.now()
    
    def start_session(self, session_id: str) -> bool:
        """Start scraping for a session"""
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            if session['status'] == 'running':
                return True
            
            # Submit to thread pool instead of creating threads directly
            if session['scraper_type'] == 'api':
                future = self.thread_pool.submit(
                    self._run_api_scraper_thread,
                    session['url'],
                    session_id
                )
            elif session['scraper_type'] == 'main':
                future = self.thread_pool.submit(
                    self._run_main_scraper_thread,
                    session['url'],
                    session_id
                )
            else:
                future = self.thread_pool.submit(
                    self._run_html_scraper_thread,
                    session['url'],
                    session_id
                )
            
            session['thread'] = future
            session['status'] = 'running'
            session['last_activity'] = datetime.now()
            
        logger.info(f"Started {session['scraper_type']} scraping for session {session_id}")
        return True
    
    def stop_session(self, session_id: str) -> bool:
        """Stop scraping for a session"""
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            
            # Set the stop event
            if 'stop_event' in session:
                session['stop_event'].set()
            
            session['status'] = 'stopping'
            
            # Signal appropriate scraper to stop (if they support it)
            if session['scraper_type'] == 'api':
                try:
                    api_scraper.stop_scraping(session_id)
                except:
                    pass

            elif session['scraper_type'] == 'main':
                try:
                    main_scraper.stop_main_scraping(session_id)
                except:
                    pass
                    
            else:
                try:
                    scraper.stop_scraping(session_id)
                except:
                    pass
            
        logger.info(f"Stopped {session['scraper_type']} scraping for session {session_id}")
        return True
    
    def remove_session(self, session_id: str):
        """Remove a session completely"""
        with self.lock:
            if session_id in self.sessions:
                self.stop_session(session_id)
                
                # Wait a bit for graceful shutdown
                time.sleep(1)
                
                del self.sessions[session_id]
                logger.info(f"Removed session {session_id}")
    
    def update_activity(self, session_id: str):
        """Update last activity time for a session"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['last_activity'] = datetime.now()
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        with self.lock:
            session = self.sessions.get(session_id, {})
            # Create a copy without the thread object for JSON serialization
            return {k: v for k, v in session.items() if k not in ['thread', 'stop_event']}
    
    def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions"""
        with self.lock:
            return {sid: {
                'url': session['url'],
                'status': session['status'],
                'created_at': session['created_at'].isoformat(),
                'last_activity': session['last_activity'].isoformat(),
                'scraper_type': session['scraper_type'],
                'run_mode': 'once' if session.get('run_once', False) else 'continuous'  # Add this line
            } for sid, session in self.sessions.items()}

    
    def cleanup_inactive_sessions(self):
        """Remove sessions that have been inactive for too long"""
        cutoff_time = datetime.now() - timedelta(minutes=30)  # 30 minute timeout
        to_remove = []
        
        with self.lock:
            for session_id, session in self.sessions.items():
                if session['last_activity'] < cutoff_time:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            logger.info(f"Cleaning up inactive session: {session_id}")
            self.remove_session(session_id)
    
    def start_cleanup_thread(self):
        """Start background thread for cleanup"""
        def cleanup_worker():
            while True:
                try:
                    self.cleanup_inactive_sessions()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
                    time.sleep(60)
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()

# Initialize session manager
session_manager = SessionManager()

# Set up scraper callback
scraper.set_socketio_and_session_manager(socketio, session_manager)
api_scraper.set_socketio_and_session_manager(socketio, session_manager)
main_scraper.set_socketio_and_session_manager(socketio, session_manager)

# API Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })
@app.route('/start', methods=['POST'])
def start_scraping():
    """Start a new scraping session"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        client_id = data.get('client_id')  # Optional client identifier
        run_once = data.get('run_once', False)  # Add this line
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Create and start session
        session_id = session_manager.create_session(url, client_id, use_api=True, use_main=True, run_once=run_once)  # Add run_once parameter
        
        if session_manager.start_session(session_id):
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "url": url,
                "scraper_type": "main",
                "run_mode": "once" if run_once else "continuous",  # Add this line
                "message": f"Event info scraping started ({'once' if run_once else 'continuous'} mode)"
            })
        else:
            return jsonify({"error": "Failed to start scraping"}), 500
            
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/start-results', methods=['POST'])
def start_results_scraping():
    """Start API scraping for results"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        results_url = data.get('results_url', '').strip()
        client_id = data.get('client_id')  # Optional client identifier
        run_once = data.get('run_once', False)  # Add this line
        
        if not results_url:
            return jsonify({"error": "results_url is required"}), 400
        
        # Create and start session with API scraper
        session_id = session_manager.create_session(results_url, client_id, use_api=True, use_main=False, run_once=run_once)  # Add run_once parameter
        
        if session_manager.start_session(session_id):
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "results_url": results_url,
                "scraper_type": "api",
                "run_mode": "once" if run_once else "continuous",  # Add this line
                "message": f"Results scraping started ({'once' if run_once else 'continuous'} mode)"
            })
        else:
            return jsonify({"error": "Failed to start results scraping"}), 500
            
    except Exception as e:
        logger.error(f"Error starting results scraping: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/discover-only', methods=['POST'])
def discover_only():
    """Discover API URLs and return them directly without starting continuous scraping"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        logger.info(f"Starting API discovery for URL: {url}")
        
        # Create a temporary scraper instance for discovery
        discovery_scraper = api_scraper.ClubSpotAPIScraper()
        
        # Use asyncio to run the discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the discovery
            discovery_successful = loop.run_until_complete(
                discovery_scraper.discover_api_urls(url)
            )
            
            if discovery_successful:
                # Format the response to match your SwiftUI models
                formatted_api_urls = {}
                for combo_key, api_info in discovery_scraper.api_urls.items():
                    formatted_api_urls[combo_key] = {
                        "url": api_info['url'],
                        "params": api_info['params']
                    }
                
                response = {
                    "status": "success",
                    "api_urls": formatted_api_urls,
                    "combinations": discovery_scraper.dropdown_combinations,
                    "message": f"Discovered {len(formatted_api_urls)} API URLs with {len(discovery_scraper.dropdown_combinations)} dropdown combinations"
                }
                
                logger.info(f"API discovery successful: {len(formatted_api_urls)} URLs found")
                return jsonify(response)
            else:
                return jsonify({
                    "status": "error",
                    "error": "Failed to discover API URLs",
                    "api_urls": {},
                    "combinations": []
                }), 500
                
        finally:
            # Clean up the event loop
            try:
                loop.close()
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error in discover-only route: {e}")
        return jsonify({
            "status": "error", 
            "error": "Internal server error",
            "api_urls": {},
            "combinations": []
        }), 500
    

    
@app.route('/stop', methods=['POST'])
def stop_scraping():
    """Stop a scraping session"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        if session_manager.stop_session(session_id):
            return jsonify({
                "status": "success",
                "session_id": session_id,
                "message": "Scraping stopped"
            })
        else:
            return jsonify({"error": "Session not found"}), 404
            
    except Exception as e:
        logger.error(f"Error stopping scraping: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """Get status of a specific session"""
    try:
        session_info = session_manager.get_session_info(session_id)
        
        if not session_info:
            return jsonify({"error": "Session not found"}), 404
        
        # Update activity since client is checking status
        session_manager.update_activity(session_id)
        
        return jsonify({
            "session_id": session_id,
            "status": session_info.get('status', 'unknown'),
            "url": session_info.get('url'),
            "scraper_type": session_info.get('scraper_type'),
            "run_mode": 'once' if session_info.get('run_once', False) else 'continuous',  # Add this line
            "created_at": session_info.get('created_at', datetime.now()).isoformat(),
            "last_activity": session_info.get('last_activity', datetime.now()).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions (for monitoring/debugging)"""
    try:
        return jsonify({
            "active_sessions": session_manager.list_active_sessions(),
            "total_count": len(session_manager.sessions)
        })
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({"error": "Internal server error"}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    logger.info(f"Client connected: {client_id}")
    
    emit('connection_confirmed', {
        'client_id': client_id,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    logger.info(f"Client disconnected: {client_id}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a specific session room"""
    try:
        session_id = data.get('session_id')
        if session_id and session_id in session_manager.sessions:
            join_room(session_id)
            session_manager.update_activity(session_id)
            logger.info(f"Client {request.sid} joined session {session_id}")
            
            emit('joined_session', {
                'session_id': session_id,
                'status': 'success'
            })
        else:
            emit('error', {'message': 'Invalid session_id'})
    except Exception as e:
        logger.error(f"Error joining session: {e}")
        emit('error', {'message': 'Failed to join session'})

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle client leaving a session room"""
    try:
        session_id = data.get('session_id')
        if session_id:
            leave_room(session_id)
            logger.info(f"Client {request.sid} left session {session_id}")
            
            emit('left_session', {
                'session_id': session_id,
                'status': 'success'
            })
    except Exception as e:
        logger.error(f"Error leaving session: {e}")
        emit('error', {'message': 'Failed to leave session'})

# Custom error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🏁 Starting Regatta Results Scraper Server")
    logger.info("=" * 50)
    logger.info("Server will be available at: http://0.0.0.0:5000")
    logger.info("API Endpoints:")
    logger.info("  POST /start     - Start event info scraping")
    logger.info("  POST /start-results - Start results scraping")
    logger.info("  POST /stop      - Stop scraping") 
    logger.info("  GET  /status/<session_id> - Get session status")
    logger.info("  GET  /sessions  - List all sessions")
    logger.info("  GET  /health    - Health check")
    logger.info("=" * 50)
    
    try:
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=False,  # Set to True for development
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")