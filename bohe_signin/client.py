from http import HTTPStatus
from urllib.parse import urlparse

from curl_cffi import requests, BrowserTypeLiteral

from utils.logger import setup_logger

IMPERSONATE: BrowserTypeLiteral = "firefox"


class BoheSignClient:
    def __init__(self, base_url: str = "https://up.x666.me", impersonate: BrowserTypeLiteral = "firefox") -> None:
        self.base_url = base_url
        self.logger = setup_logger()
        self._session = requests.AsyncSession()

    def import_session_cookies(self, auth_token: str | None) -> None:
        if not auth_token:
            return

        self._session.cookies.set(
            "auth_token", auth_token, domain=urlparse(self.base_url).hostname, secure=True
        )

    async def fetch_info(self) -> requests.Response:
        return await self._session.get(
            f"{self.base_url}/api/user/info",
            impersonate=IMPERSONATE,
        )

    async def get_checkin_status(self) -> requests.Response:
        return await self._session.get(
            f"{self.base_url}/api/checkin/status",
            impersonate=IMPERSONATE,
        )

    async def signin(self) -> requests.Response:
        return await self._session.post(
            f"{self.base_url}/api/checkin/spin",
            headers={
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/",
            },
            impersonate=IMPERSONATE,
        )

    async def verify_session(self) -> tuple[bool, str]:
        r = await self.fetch_info()
        return r.status_code == HTTPStatus.OK and r.json().get("success"), r.text
