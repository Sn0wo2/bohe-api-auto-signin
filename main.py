import asyncio
import random
import sys

from client import BoheClient
from store.token import Account, load_accounts, save_accounts
from utils.logger import setup_logger

logger = setup_logger()


async def _process_account(account: Account) -> bool:
    async with BoheClient(account) as client:
        await client.authenticate()
        return await client.signin()


async def main():
    accounts = load_accounts()
    logger.info(f"Loaded {len(accounts)} account(s)")

    results: list[tuple[str, bool]] = []
    try:
        for index, account in enumerate(accounts):
            logger.info(f"[{account.name}] Processing account {index + 1}/{len(accounts)}")
            try:
                ok = await _process_account(account)
            except Exception:
                logger.exception(f"[{account.name}] Account processing failed")
                ok = False
            results.append((account.name, ok))

            if index < len(accounts) - 1:
                delay = random.uniform(5, 20)
                logger.info(f"Sleeping {delay:.0f}s before next account...")
                await asyncio.sleep(delay)
    finally:
        # Persist refreshed cookies/tokens even on partial progress.
        save_accounts(accounts)

    succeeded = [name for name, ok in results if ok]
    failed = [name for name, ok in results if not ok]
    logger.info(f"Done: {len(succeeded)} succeeded, {len(failed)} failed")
    if failed:
        logger.warning(f"Failed accounts: {', '.join(failed)}")
    if not succeeded:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
