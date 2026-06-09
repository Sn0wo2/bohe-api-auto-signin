import re
import time
from http import HTTPStatus
from urllib.parse import urljoin

from curl_cffi import requests
from linux_do_connect import IMPERSONATE, LinuxDoConnect

from utils.logger import setup_logger

class OAuthError(Exception):
    def __init__(self, status_code: int, message: str = "OAuth approval failed"):
        self.status_code = status_code
        super().__init__(message)

class BoheSignClient:
    BASE_URL = "https://up.x666.me"

    def __init__(self):
        self.logger = setup_logger()
        self._session: requests.AsyncSession | None = None

    async def __aenter__(self):
        self._session = requests.AsyncSession()
        return self

    async def __aexit__(self, *exc):
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> requests.AsyncSession:
        if self._session is None:
            raise RuntimeError("BoheSignClient must be used as async context manager")
        return self._session

    def import_session_cookies(self, auth_token: str | None) -> None:
        if not auth_token:
            return
        self.session.cookies.set("auth_token", auth_token, domain="up.x666.me", secure=True)

    def export_session_cookies(self) -> str:
        for cookie in self.session.cookies.jar:
            if "x666.me" in cookie.domain and cookie.name == "auth_token" and cookie.value:
                return cookie.value
        return ""

    async def fetch_info(self) -> requests.Response:
        return await self.session.get(
            f"{self.BASE_URL}/api/user/info",
            impersonate=IMPERSONATE,
        )

    async def get_checkin_status(self) -> requests.Response:
        return await self.session.get(
            f"{self.BASE_URL}/api/checkin/status",
            impersonate=IMPERSONATE,
        )

    async def signin(self) -> requests.Response:
        return await self.session.post(
            f"{self.BASE_URL}/api/checkin/spin",
            impersonate=IMPERSONATE,
        )

    async def verify_session(self) -> tuple[bool, str]:
        r = await self.fetch_info()
        return r.status_code == HTTPStatus.OK and r.json().get("success"), r.text

    async def authenticate(self, connect_token: str) -> None:
        r = await self.session.get(
            f"{self.BASE_URL}/api/auth/login",
            impersonate=IMPERSONATE,
        )

        auth_url = r.json().get("auth_url")
        if not auth_url:
            raise ValueError("Failed to get auth_url")

        ld_auth = LinuxDoConnect()
        ld_auth.set_connect_token(connect_token)

        try:
            approve_url = await ld_auth.approve_oauth(auth_url)
        except ValueError as e:
            status_match = re.search(r"status=(\d+)", str(e))
            status_code = int(status_match.group(1)) if status_match else 0
            raise OAuthError(status_code) from e

        if not approve_url:
            raise ValueError("Failed to get approve_url")

        r = await self.session.get(approve_url, impersonate=IMPERSONATE, allow_redirects=False)

        location = r.headers.get("Location")
        if location:
            redirect_url = urljoin(approve_url, location)
            r = await self.session.get(
                redirect_url,
                impersonate=IMPERSONATE,
                allow_redirects=True,
            )

        valid, _ = await self.verify_session()
        if valid:
            self.logger.info("Authenticated successfully")
            return

        raise ValueError(f"Failed to obtain Bohe session, status={r.status_code}")
