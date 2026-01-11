"""Ollama service lifecycle manager with proper cleanup"""

import subprocess
import atexit
import logging
import time
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class OllamaServiceManager:
    """Manages Ollama service lifecycle with automatic cleanup"""
    
    _instance = None
    _process: Optional[subprocess.Popen] = None
    _registered_cleanup = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only register cleanup once
        if not self.__class__._registered_cleanup:
            atexit.register(self.stop)
            self.__class__._registered_cleanup = True
    
    def is_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=2)
            return response.status_code == 200
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            return False
    
    def start(self) -> bool:
        """Start Ollama service if not running"""
        if self.is_running():
            logger.info("Ollama service is already running")
            return True
        
        logger.info("Starting Ollama service...")
        
        try:
            # Start the service
            self.__class__._process = subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent process group
            )
            
            # Wait for service to be ready
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(1)
                if self.is_running():
                    logger.info("✓ Ollama service started successfully")
                    return True
                if self.__class__._process.poll() is not None:
                    # Process has terminated
                    logger.error("Ollama service failed to start")
                    self.__class__._process = None
                    return False
            
            logger.warning("Ollama service started but not responding")
            return False
            
        except FileNotFoundError:
            logger.error("Ollama not found. Please install it first.")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama service: {e}")
            return False
    
    def stop(self):
        """Stop Ollama service if we started it"""
        if self.__class__._process:
            logger.info("Stopping Ollama service...")
            try:
                # Try graceful termination first
                self.__class__._process.terminate()
                try:
                    self.__class__._process.wait(timeout=5)
                    logger.info("✓ Ollama service stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning("Forcing Ollama service termination...")
                    self.__class__._process.kill()
                    self.__class__._process.wait(timeout=2)
                    logger.info("✓ Ollama service forcefully terminated")
            except Exception as e:
                logger.error(f"Error stopping Ollama service: {e}")
            finally:
                self.__class__._process = None
    
    def restart(self) -> bool:
        """Restart Ollama service"""
        self.stop()
        time.sleep(2)  # Brief pause before restart
        return self.start()
    
    def get_status(self) -> dict:
        """Get detailed status of Ollama service"""
        status = {
            "running": self.is_running(),
            "managed": self.__class__._process is not None,
            "pid": self.__class__._process.pid if self.__class__._process else None
        }
        
        if status["running"]:
            try:
                # Get available models
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    status["models"] = [m['name'] for m in models]
                    status["model_count"] = len(models)
            except Exception as e:
                logger.debug(f"Could not get model list: {e}")
        
        return status

# Create singleton instance
ollama_service = OllamaServiceManager()