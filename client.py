from http import HTTPStatus

from bohe_signin.client import BoheSignClient
from store.token import Account
from utils.logger import setup_logger


def _fmt_quota(quota: int) -> str:
    """把额度同时格式化为 quota 与「次」，例如 150000 -> '150000quota(300times)'。"""
    return f"{quota}quota({quota // 500}times)"


class BoheClient:
    def __init__(self, account: Account, index: int = 0):
        self.account = account
        self.index = index
        self.logger = setup_logger()
        self.signin_client = BoheSignClient()

    @property
    def _tag(self) -> str:
        return f"[account{self.index + 1}] "

    async def authenticate(self) -> None:
        auth_token = self.account.bohe_session_cookies
        if not auth_token:
            raise ValueError(
                f"{self._tag}bohe_session_cookies is required "
                "(OAuth refresh removed; set it manually)"
            )
        self.logger.info(f"{self._tag}Verifying Bohe session...")
        self.signin_client.import_session_cookies(auth_token)
        valid, _ = await self.signin_client.verify_session()
        if not valid:
            raise RuntimeError(
                f"{self._tag}Bohe session invalid or expired; "
                "please manually update bohe_session_cookies"
            )
        self.logger.info(f"{self._tag}Bohe session cookies are valid")

    async def signin(self) -> bool:
        try:
            self.logger.info(f"{self._tag}Checking check-in status...")
            status_r = await self.signin_client.get_checkin_status()
            if status_r.status_code == HTTPStatus.OK:
                status_data = status_r.json()
                if not status_data.get("can_spin"):
                    self.logger.info(
                        f"{self._tag}Already checked in today (confirmed by server)"
                    )
                    return True
                # 必出大奖进度（与前端能量槽同源的 pity_days_left 字段）：签到前提示距离保底还差几天
                days_left = status_data.get("pity_days_left")
                if isinstance(days_left, int) and 0 < days_left <= 1:
                    self.logger.info(
                        f"{self._tag}Pity ready: next spin guarantees the jackpot"
                    )
                elif isinstance(days_left, int) and days_left > 0:
                    self.logger.info(
                        f"{self._tag}Pity progress: {days_left} day(s) left until guaranteed jackpot"
                    )
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
                    log_parts = [
                        f"{self._tag}Signin: {prefix}{data.get('label')} +{_fmt_quota(quota)}"
                    ]
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
