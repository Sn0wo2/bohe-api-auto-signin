"""Regression tests for client.py (BoheClient) — lock observable behavior before slop removal."""
import unittest
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

from client import BoheClient, _fmt_quota
from store.token import Account


class TestFmtQuota(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_fmt_quota(150000), "150000quota(300times)")

    def test_zero(self):
        self.assertEqual(_fmt_quota(0), "0quota(0times)")

    def test_below_500(self):
        self.assertEqual(_fmt_quota(499), "499quota(0times)")


def _make_client(cookies: str = "test-cookie") -> BoheClient:
    with patch("client.setup_logger", return_value=MagicMock()), patch(
        "client.BoheSignClient"
    ) as mock_cls:
        mock_cls.return_value = MagicMock()
        return BoheClient(Account(bohe_session_cookies=cookies), 0)


class TestAuthenticate(unittest.IsolatedAsyncioTestCase):
    async def test_no_cookies_raises_value_error(self):
        client = _make_client(cookies="")
        with self.assertRaises(ValueError):
            await client.authenticate()

    async def test_valid_session_passes(self):
        client = _make_client(cookies="good")
        client.signin_client.verify_session = AsyncMock(return_value=(True, "ok"))
        await client.authenticate()

    async def test_invalid_session_raises_runtime_error(self):
        client = _make_client(cookies="bad")
        client.signin_client.verify_session = AsyncMock(return_value=(False, "expired"))
        with self.assertRaises(RuntimeError):
            await client.authenticate()

    async def test_imports_cookies_before_verify(self):
        client = _make_client(cookies="good")
        client.signin_client.verify_session = AsyncMock(return_value=(True, "ok"))
        await client.authenticate()
        client.signin_client.import_session_cookies.assert_called_once_with("good")


def _mock_response(status_code: int, json_data: dict | None = None, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


class TestSignin(unittest.IsolatedAsyncioTestCase):
    async def test_already_checked_in_returns_true(self):
        client = _make_client()
        client.signin_client.get_checkin_status = AsyncMock(
            return_value=_mock_response(HTTPStatus.OK, {"can_spin": False})
        )
        client.signin_client.signin = AsyncMock(return_value=_mock_response(HTTPStatus.OK))
        self.assertTrue(await client.signin())
        client.signin_client.signin.assert_not_called()

    async def test_successful_signin_returns_true(self):
        client = _make_client()
        client.signin_client.get_checkin_status = AsyncMock(
            return_value=_mock_response(HTTPStatus.OK, {"can_spin": True})
        )
        client.signin_client.signin = AsyncMock(
            return_value=_mock_response(
                HTTPStatus.OK,
                {"success": True, "label": "day1", "quota": 500, "new_balance": 1000},
            )
        )
        self.assertTrue(await client.signin())

    async def test_signin_success_false_returns_false(self):
        client = _make_client()
        client.signin_client.get_checkin_status = AsyncMock(
            return_value=_mock_response(HTTPStatus.OK, {"can_spin": True})
        )
        client.signin_client.signin = AsyncMock(
            return_value=_mock_response(HTTPStatus.OK, {"success": False, "message": "nope"})
        )
        self.assertFalse(await client.signin())

    async def test_signin_non_ok_status_returns_false(self):
        client = _make_client()
        client.signin_client.get_checkin_status = AsyncMock(
            return_value=_mock_response(HTTPStatus.INTERNAL_SERVER_ERROR)
        )
        client.signin_client.signin = AsyncMock(
            return_value=_mock_response(HTTPStatus.INTERNAL_SERVER_ERROR)
        )
        self.assertFalse(await client.signin())

    async def test_signin_exception_returns_false(self):
        """Broad except Exception in signin() must swallow errors and return False."""
        client = _make_client()
        client.signin_client.get_checkin_status = AsyncMock(side_effect=RuntimeError("network"))
        self.assertFalse(await client.signin())


if __name__ == "__main__":
    unittest.main()
