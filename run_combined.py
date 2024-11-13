import subprocess
import sys
import os
from dotenv import load_dotenv

def run_processes():
    """Run both web server and discord bot processes."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Set unbuffered output
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Start both processes
    web_process = subprocess.Popen([sys.executable, 'web.py'])
    bot_process = subprocess.Popen([sys.executable, 'bot.py'])
    
    try:
        # Wait for both processes to complete
        web_process.wait()
        bot_process.wait()
    except KeyboardInterrupt:
        # Handle graceful shutdown
        print("\nShutting down processes...")
        web_process.terminate()
        bot_process.terminate()
        web_process.wait()
        bot_process.wait()
        print("Processes terminated.")

if __name__ == '__main__':
    run_processes()
