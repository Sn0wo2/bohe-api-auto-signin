import asyncio
import random
from http import HTTPStatus

from linux_do_connect import LinuxDoConnect

from bohe_signin.client import BoheSignClient, OAuthError
from store.token import Account
from utils.logger import setup_logger

"""把额度同时格式化为 quota 与「次」，例如 150000 -> '150000quota(300times)'。"""
def _fmt_quota(quota: int) -> str:
    return f"{quota}quota({quota // 500}times)"


class BoheClient:
    def __init__(self, account: Account):
        self.account = account
        self.logger = setup_logger()
        self.signin_client = BoheSignClient()

    @property
    def _tag(self) -> str:
        return f"[{self.account.name}] "

    async def __aenter__(self):
        await self.signin_client.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self.signin_client.__aexit__(*exc)

    async def _get_connect_token(self, ld_token: str | None) -> tuple[str, str | None]:
        if not ld_token:
            raise ValueError("linux_do_token is required to refresh connect token")
        self.logger.info(f"{self._tag}Refreshing connect token with linux_do_token (len={len(ld_token)})")
        connect = LinuxDoConnect(token=ld_token)
        await connect.login()
        self.logger.info(f"{self._tag}Successfully logged in to linux.do")

        connect_token, _ = await connect.get_connect_token()
        self.logger.info(f"{self._tag}Successfully obtained connect token from linux.do")
        return connect_token, ld_token

    async def authenticate(self) -> None:
        account = self.account
        auth_token = account.bohe_session_cookies
        connect_token = account.linux_do_connect_token
        ld_token = account.linux_do_token

        self.logger.debug(f"{self._tag}Token state: auth_token={'set' if auth_token else 'empty'}, connect_token={'set' if connect_token else 'empty'}, ld_token={'set' if ld_token else 'empty'}")

        if auth_token:
            self.logger.info(f"{self._tag}Verifying existing Bohe session (auth_token)...")
            self.signin_client.import_session_cookies(auth_token)
            valid, _ = await self.signin_client.verify_session()
            if valid:
                self.logger.info(f"{self._tag}Existing Bohe session cookies are still valid")
                return
            self.logger.warning(f"{self._tag}Stored auth_token is invalid/expired, attempting to refresh...")

        for attempt in range(1, 4):
            try:
                if attempt > 1:
                    self.logger.info(f"{self._tag}Retrying Bohe session refresh (attempt {attempt}/3)...")

                if not connect_token:
                    self.logger.debug(f"{self._tag}No connect_token available, refreshing from linux_do_token")
                    connect_token, ld_token = await self._get_connect_token(ld_token)
                else:
                    self.logger.debug(f"{self._tag}Reusing existing connect_token")

                await self.signin_client.authenticate(connect_token)

                bohe_session_cookies = self.signin_client.export_session_cookies()
                if not bohe_session_cookies:
                    raise RuntimeError("Server returned no Bohe session cookies")

                account.bohe_session_cookies = bohe_session_cookies
                account.linux_do_connect_token = connect_token or ""
                account.linux_do_token = ld_token or ""
                self.logger.info(f"{self._tag}Successfully obtained auth_token")
                return
            except OAuthError as e:
                self.logger.warning(f"{self._tag}OAuth failed: status={e.status_code}")
                if e.status_code == 429:
                    if attempt == 3:
                        self.logger.error(f"{self._tag}All 3 attempts failed (rate limited). Giving up.")
                        raise
                    backoff = min(600, 60 * (2 ** (attempt - 1)) + random.uniform(0, 30))
                    self.logger.warning(
                        f"{self._tag}Rate limited on attempt {attempt}. Backing off {backoff:.0f}s before retry..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise
            except Exception:
                self.logger.warning(f"{self._tag}Bohe session refresh attempt {attempt} failed", exc_info=True)
                if attempt == 3:
                    self.logger.error(f"{self._tag}All 3 attempts to refresh Bohe session failed.")
                    raise

    async def signin(self) -> bool:
        try:
            self.logger.info(f"{self._tag}Checking check-in status...")
            status_r = await self.signin_client.get_checkin_status()
            if status_r.status_code == HTTPStatus.OK:
                status_data = status_r.json()
                if not status_data.get("can_spin"):
                    self.logger.info(f"{self._tag}Already checked in today (confirmed by server)")
                    return True
                # 必出大奖进度（与前端能量槽同源的 pity_days_left 字段）：签到前提示距离保底还差几天
                days_left = status_data.get("pity_days_left")
                if isinstance(days_left, int) and 0 < days_left <= 1:
                    self.logger.info(f"{self._tag}Pity ready: next spin guarantees the jackpot")
                elif isinstance(days_left, int) and days_left > 0:
                    self.logger.info(f"{self._tag}Pity progress: {days_left} day(s) left until guaranteed jackpot")
            self.logger.info(f"{self._tag}Ready to signin, performing spin...")

            r = await self.signin_client.signin()

            if r.status_code == HTTPStatus.OK:
                data = r.json()
                if data.get("success"):
                    balance = data.get("new_balance", 0)
                    quota = data.get("quota", 0)
                    streak = data.get("streak_days", 0)
                    rank = data.get("today_rank", 0)
                    level = data.get("level")
                    month_days = data.get("month_days", 0)
                    milestone_bonus = data.get("milestone_bonus", 0)
                    pity_hit = data.get("pity_hit", 0)
                    # pity_hit 为 1/2 表示本次命中必出大奖
                    prefix = "JACKPOT! " if pity_hit in (1, 2) else ""
                    log_parts = [f"{self._tag}Signin: {prefix}{data.get('label')} +{_fmt_quota(quota)}"]
                    if level:
                        log_parts.append(f"level={level}")
                    if milestone_bonus:
                        log_parts.append(f"milestone+{_fmt_quota(milestone_bonus)}")
                    if balance:
                        log_parts.append(f"bal={_fmt_quota(balance)}")
                    if streak:
                        log_parts.append(f"streak={streak}d")
                    if month_days:
                        log_parts.append(f"month={month_days}d")
                    if rank:
                        log_parts.append(f"rank=#{rank}")
                    self.logger.info(", ".join(log_parts))
                    return True
                self.logger.warning(f"{self._tag}Signin failed: {data.get('message')}")
            else:
                self.logger.error(f"{self._tag}Signin error: {r.status_code}")
        except Exception:
            self.logger.error(f"{self._tag}Signin exception", exc_info=True)
        return False
