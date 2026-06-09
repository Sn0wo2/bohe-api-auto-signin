import asyncio
import sys

from client import BoheClient
from utils.logger import setup_logger

logger = setup_logger()


async def main():
    try:
        async with BoheClient() as client:
            await client.authenticate()
            await client.signin()
    except Exception:
        logger.exception("Critical error in main")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
