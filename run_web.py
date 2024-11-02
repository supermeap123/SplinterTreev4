from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from web.app import app

async def main():
    config = Config()
    config.bind = ["0.0.0.0:5002"]
    config.use_reloader = True
    
    print("Starting web UI on http://localhost:5002")
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
