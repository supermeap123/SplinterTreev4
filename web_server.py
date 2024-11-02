import os
import logging
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from web.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

async def main():
    try:
        port = int(os.environ.get('PORT', 5000))
        config = Config()
        config.bind = [f"0.0.0.0:{port}"]
        config.use_reloader = False
        config.accesslog = '-'  # Log to stdout
        
        logger.info(f"Starting web UI on port {port}")
        await serve(app, config)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
