import asyncio
import os
import random
from http import HTTPStatus

from linux_do_connect import LinuxDoConnect

from bohe_signin.client import BoheSignClient
from store.token import load_tokens, save_tokens
from utils.logger import setup_logger


class BoheClient:
    def __init__(self):
        self.logger = setup_logger()
        self.signin_client = BoheSignClient()

    async def __aenter__(self):
        await self.signin_client.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self.signin_client.__aexit__(*exc)

    async def _get_connect_token(self, ld_token: str | None) -> tuple[str, str | None]:
        if not ld_token:
            raise ValueError("LINUX_DO_TOKEN is required to refresh connect token")
        self.logger.info(f"Refreshing connect token with linux_do_token (len={len(ld_token)})")
        connect = LinuxDoConnect(token=ld_token)
        await connect.login()
        self.logger.info("Successfully logged in to linux.do")

        connect_token, _ = await connect.get_connect_token()
        self.logger.info("Successfully obtained connect token from linux.do")
        return connect_token, ld_token

    async def authenticate(self) -> None:
        tokens = load_tokens()
        auth_token = tokens.get("bohe_session_cookies")
        connect_token_value = tokens.get("linux_do_connect_token")
        ld_token_value = tokens.get("linux_do_token")
        connect_token = connect_token_value if isinstance(connect_token_value, str) and connect_token_value else None
        ld_token = ld_token_value if isinstance(ld_token_value, str) and ld_token_value else None
        connect_token = connect_token or os.getenv("LINUX_DO_CONNECT_TOKEN")
        ld_token = ld_token or os.getenv("LINUX_DO_TOKEN")

        if isinstance(auth_token, str) and auth_token:
            self.logger.info("Verifying existing Bohe session (auth_token)...")
            self.signin_client.import_session_cookies(auth_token)
            valid, _ = await self.signin_client.verify_session()
            if valid:
                self.logger.info("Existing Bohe session cookies are still valid")
                return
            self.logger.warning("Stored auth_token is invalid/expired, attempting to refresh...")

        for attempt in range(1, 4):
            try:
                if attempt > 1:
                    self.logger.info(f"Retrying Bohe session refresh (attempt {attempt}/3)...")

                if not connect_token or attempt > 1:
                    connect_token, ld_token = await self._get_connect_token(ld_token)

                await self.signin_client.authenticate(connect_token)

                bohe_session_cookies = self.signin_client.export_session_cookies()
                if not bohe_session_cookies:
                    raise RuntimeError("Server returned no Bohe session cookies")

                save_tokens(
                    bohe_session_cookies=bohe_session_cookies,
                    linux_do_connect_token=connect_token,
                    linux_do_token=ld_token,
                )
                self.logger.info("Successfully obtained and saved auth_token")
                return
            except ValueError as e:
                if "rate limited" in str(e).lower():
                    if attempt == 3:
                        self.logger.error("All 3 attempts failed (rate limited). Giving up.")
                        raise
                    backoff = min(300, 30 * (2 ** (attempt - 1)) + random.uniform(0, 10))
                    self.logger.warning(
                        f"Rate limited on attempt {attempt}. Backing off {backoff:.0f}s before retry..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise
            except Exception:
                self.logger.warning(f"Bohe session refresh attempt {attempt} failed", exc_info=True)
                if attempt == 3:
                    self.logger.error("All 3 attempts to refresh Bohe session failed.")
                    raise

    async def signin(self) -> bool:
        try:
            self.logger.info("Checking check-in status...")
            status_r = await self.signin_client.get_checkin_status()
            if status_r.status_code == HTTPStatus.OK:
                status_data = status_r.json()
                if not status_data.get("can_spin"):
                    self.logger.info("Already checked in today (confirmed by server)")
                    return True
            self.logger.info("Ready to signin, performing spin...")

            r = await self.signin_client.signin()

            if r.status_code == HTTPStatus.OK:
                data = r.json()
                if data.get("success"):
                    balance = data.get("new_balance", 0)
                    balance_times = balance // 500
                    streak = data.get("streak_days", 0)
                    rank = data.get("today_rank", 0)
                    log_parts = [f"Signin: {data.get('label')} +{data.get('quota')}quota"]
                    if balance:
                        log_parts.append(f"bal={balance_times}times")
                    if streak:
                        log_parts.append(f"streak={streak}d")
                    if rank:
                        log_parts.append(f"rank=#{rank}")
                    self.logger.info(", ".join(log_parts))
                    return True
                self.logger.warning(f"Signin failed: {data.get('message')}")
            else:
                self.logger.error(f"Signin error: {r.status_code}")
        except Exception:
            self.logger.error("Signin exception", exc_info=True)
        return False
