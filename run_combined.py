import subprocess
import sys
import os
import time
import signal
import logging
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/combined.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_web_server(url="http://localhost:5000", timeout=1):
    """Check if web server is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200 or response.status_code == 401  # 401 is ok as it means auth is working
    except RequestException:
        return False

def stream_process_output(process, name):
    """Stream the output of a process in real-time"""
    for stdout_line in iter(process.stdout.readline, ""):
        logger.info(f"{name} stdout: {stdout_line.strip()}")
    for stderr_line in iter(process.stderr.readline, ""):
        logger.error(f"{name} stderr: {stderr_line.strip()}")

def run_processes():
    """Run both web server and discord bot processes with proper handling."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Set unbuffered output
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Initialize database if needed
    logger.info("Initializing database...")
    try:
        subprocess.run([sys.executable, 'initialize_interaction_logs_db.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    processes = []
    try:
        # Start web server first
        logger.info("Starting web server...")
        web_process = subprocess.Popen(
            [sys.executable, 'web.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        processes.append(('web', web_process))
        
        # Wait for web server to be ready
        logger.info("Waiting for web server to be ready...")
        retries = 30
        while retries > 0:
            if check_web_server():
                logger.info("Web server is ready")
                break
            time.sleep(1)
            retries -= 1
            if web_process.poll() is not None:
                stdout, stderr = web_process.communicate()
                logger.error(f"Web server failed to start\nStdout: {stdout}\nStderr: {stderr}")
                return
        else:
            logger.error("Web server failed to respond in time")
            return
        
        # Start Discord bot
        logger.info("Starting Discord bot...")
        bot_process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        processes.append(('bot', bot_process))
        
        # Stream bot process output in real-time
        stream_process_output(bot_process, 'bot')
        
        # Monitor processes
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    logger.error(f"{name} process died\nStdout: {stdout}\nStderr: {stderr}")
                    raise Exception(f"{name} process died unexpectedly")
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal...")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        # Graceful shutdown
        logger.info("Shutting down processes...")
        for name, process in processes:
            if process.poll() is None:  # If process is still running
                logger.info(f"Terminating {name} process...")
                if sys.platform == 'win32':
                    process.terminate()  # Use SIGTERM on Windows
                else:
                    process.send_signal(signal.SIGTERM)  # Use SIGTERM on Unix
                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds for graceful shutdown
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} process didn't terminate gracefully, forcing...")
                    process.kill()  # Force kill if process doesn't terminate
                    process.wait()
        logger.info("All processes terminated.")

if __name__ == '__main__':
    run_processes()
