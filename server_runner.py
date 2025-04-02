#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
from server import configure_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)
logger = logging.getLogger("ServerRunner")

# Parse allowed directories
allowed_dirs = sys.argv[1:] if len(sys.argv) > 1 else []
if allowed_dirs:
    logger.info(f"Using allowed directories: {allowed_dirs}")
else:
    logger.info("No directories specified. File access will be restricted.")

# Configure and run server
async def main():
    server = configure_server(allowed_dirs=allowed_dirs)
    await server.run()

if __name__ == "__main__":
    # Set Windows event loop policy if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
