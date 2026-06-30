import asyncio
import random
import sys

from client import BoheClient
from store.token import load_accounts
from utils.logger import setup_logger

logger = setup_logger()


async def main():
    accounts = load_accounts()
    logger.info(f"Loaded {len(accounts)} account(s)")

    results: list[tuple[int, bool]] = []
    for index, account in enumerate(accounts):
        logger.info(
            f"[account{index + 1}] Processing account {index + 1}/{len(accounts)}"
        )
        try:
            client = BoheClient(account, index)
            await client.authenticate()
            ok = await client.signin()
        except Exception:
            logger.exception(f"[account{index + 1}] Account processing failed")
            ok = False
        results.append((index, ok))

        if index < len(accounts) - 1:
            delay = random.uniform(5, 20)
            logger.info(f"Sleeping {delay:.0f}s before next account...")
            await asyncio.sleep(delay)

    succeeded = [idx for idx, ok in results if ok]
    failed = [idx for idx, ok in results if not ok]
    logger.info(f"Done: {len(succeeded)} succeeded, {len(failed)} failed")
    if failed:
        logger.warning(
            f"Failed accounts: {', '.join(f'account{idx + 1}' for idx in failed)}"
        )
    if not succeeded:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
