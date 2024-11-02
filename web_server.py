import os
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from web.app import create_app

app = create_app()

async def main():
    port = int(os.environ.get('PORT', 5000))
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    config.use_reloader = False  # Disable reloader in production
    
    print(f"Starting web UI on port {port}")
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
