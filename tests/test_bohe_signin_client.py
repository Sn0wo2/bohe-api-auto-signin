"""Regression tests for bohe_signin/client.py — lock observable behavior before slop removal."""
import unittest
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

from bohe_signin.client import BoheSignClient


def _make_client() -> BoheSignClient:
    with patch("bohe_signin.client.requests.AsyncSession") as mock_session_cls, patch(
        "bohe_signin.client.setup_logger"
    ) as mock_logger:
        mock_session_cls.return_value = MagicMock()
        mock_logger.return_value = MagicMock()
        return BoheSignClient()


class TestImportSessionCookies(unittest.TestCase):
    def test_none_is_noop(self):
        client = _make_client()
        client.import_session_cookies(None)
        client._session.cookies.set.assert_not_called()

    def test_empty_string_is_noop(self):
        client = _make_client()
        client.import_session_cookies("")
        client._session.cookies.set.assert_not_called()

    def test_sets_auth_token_cookie(self):
        client = _make_client()
        client.import_session_cookies("my-token")
        client._session.cookies.set.assert_called_once()
        args, kwargs = client._session.cookies.set.call_args
        self.assertEqual(args[0], "auth_token")
        self.assertEqual(args[1], "my-token")
        self.assertTrue(kwargs.get("secure"))


class TestVerifySession(unittest.IsolatedAsyncioTestCase):
    async def test_valid_session(self):
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.json.return_value = {"success": True}
        resp.text = '{"success": true}'
        client._session.get = AsyncMock(return_value=resp)
        valid, text = await client.verify_session()
        self.assertTrue(valid)
        self.assertEqual(text, '{"success": true}')

    async def test_non_ok_status(self):
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.UNAUTHORIZED
        resp.text = "unauthorized"
        client._session.get = AsyncMock(return_value=resp)
        valid, _ = await client.verify_session()
        self.assertFalse(valid)

    async def test_ok_but_success_false(self):
        client = _make_client()
        resp = MagicMock()
        resp.status_code = HTTPStatus.OK
        resp.json.return_value = {"success": False}
        resp.text = '{"success": false}'
        client._session.get = AsyncMock(return_value=resp)
        valid, _ = await client.verify_session()
        self.assertFalse(valid)


class TestApiCalls(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_info_hits_user_info(self):
        client = _make_client()
        client._session.get = AsyncMock(return_value=MagicMock())
        await client.fetch_info()
        client._session.get.assert_called_once()
        url = client._session.get.call_args.args[0]
        self.assertIn("/api/user/info", url)

    async def test_get_checkin_status_hits_status_endpoint(self):
        client = _make_client()
        client._session.get = AsyncMock(return_value=MagicMock())
        await client.get_checkin_status()
        url = client._session.get.call_args.args[0]
        self.assertIn("/api/checkin/status", url)

    async def test_signin_hits_spin_endpoint(self):
        client = _make_client()
        client._session.post = AsyncMock(return_value=MagicMock())
        await client.signin()
        url = client._session.post.call_args.args[0]
        self.assertIn("/api/checkin/spin", url)


if __name__ == "__main__":
    unittest.main()
