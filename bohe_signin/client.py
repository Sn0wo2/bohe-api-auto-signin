import re
from http import HTTPStatus
from urllib.parse import urljoin

from curl_cffi import requests
from linux_do_connect import IMPERSONATE, LinuxDoConnect

from utils.logger import setup_logger


class OAuthError(Exception):
    def __init__(
        self,
        status_code: int = HTTPStatus.UNAUTHORIZED,
        message: str = "OAuth approval failed",
    ):
        self.status_code = status_code
        super().__init__(message)


class BoheSignClient:
    def __init__(self, base_url: str = "https://up.x666.me"):
        self.base_url = base_url
        self.logger = setup_logger()
        self._session = requests.AsyncSession()

    def import_session_cookies(self, auth_token: str | None) -> None:
        if not auth_token:
            return
        self._session.cookies.set(
            "auth_token", auth_token, domain=self.base_url, secure=True
        )

    def export_session_cookies(self) -> str:
        for cookie in self._session.cookies.jar:
            if (
                self.base_url in cookie.domain
                and cookie.name == "auth_token"
                and cookie.value
            ):
                return cookie.value
        return ""

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

    async def authenticate(self, connect_token: str) -> None:
        r = await self._session.get(
            f"{self.base_url}/api/auth/login",
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

        r = await self._session.get(
            approve_url, impersonate=IMPERSONATE, allow_redirects=False
        )

        location = r.headers.get("Location")
        if location:
            self.logger.info(f"Redirecting to {location}")
            redirect_url = urljoin(approve_url, location)
            r = await self._session.get(
                redirect_url,
                impersonate=IMPERSONATE,
                allow_redirects=True,
            )

        valid, _ = await self.verify_session()
        if valid:
            self.logger.info("Authenticated successfully")
            return

        raise ValueError(f"Failed to obtain Bohe session, status={r.status_code}")
