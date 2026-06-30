"""Regression tests for store/token.py — lock observable behavior before slop removal."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from store.token import (
    Account,
    _load_accounts_from_env,
    _load_accounts_from_file,
    _parse_roster,
    _write_accounts_to_file,
    load_accounts,
)


class TestAccount(unittest.TestCase):
    def test_cookies_default_empty(self):
        self.assertEqual(Account().bohe_session_cookies, "")

    def test_cookies_stripped(self):
        self.assertEqual(Account(bohe_session_cookies="  abc  ").bohe_session_cookies, "abc")

    def test_extra_fields_ignored(self):
        acc = Account(
            bohe_session_cookies="x",
            linux_do_token="legacy",
            linux_do_connect_token="legacy2",
        )
        self.assertEqual(acc.bohe_session_cookies, "x")
        self.assertFalse(hasattr(acc, "linux_do_token"))


class TestParseRoster(unittest.TestCase):
    def test_valid_list(self):
        result = _parse_roster([{"bohe_session_cookies": "a"}, {"bohe_session_cookies": "b"}])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].bohe_session_cookies, "a")

    def test_empty_list(self):
        self.assertEqual(_parse_roster([]), [])

    def test_invalid_item_returns_empty(self):
        self.assertEqual(_parse_roster([{"bohe_session_cookies": "a"}, "not-a-dict"]), [])


class TestLoadFromEnv(unittest.TestCase):
    def test_no_env_returns_none(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BOHE_ACCOUNTS", None)
            self.assertIsNone(_load_accounts_from_env())

    def test_valid_json(self):
        with patch.dict(os.environ, {"BOHE_ACCOUNTS": '[{"bohe_session_cookies":"x"}]'}):
            result = _load_accounts_from_env()
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].bohe_session_cookies, "x")

    def test_invalid_json_returns_none(self):
        with patch.dict(os.environ, {"BOHE_ACCOUNTS": "not json"}):
            self.assertIsNone(_load_accounts_from_env())

    def test_empty_string_returns_none(self):
        with patch.dict(os.environ, {"BOHE_ACCOUNTS": ""}):
            self.assertIsNone(_load_accounts_from_env())


class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.token_file = os.path.join(self.tmpdir, "token.json")

    def test_write_read_roundtrip(self):
        accounts = [Account(bohe_session_cookies="abc"), Account(bohe_session_cookies="def")]
        with patch("store.token.TOKEN_FILE", self.token_file):
            _write_accounts_to_file(accounts)
            loaded = _load_accounts_from_file()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].bohe_session_cookies, "abc")
        self.assertEqual(loaded[1].bohe_session_cookies, "def")

    def test_missing_file_returns_empty(self):
        with patch("store.token.TOKEN_FILE", os.path.join(self.tmpdir, "nope.json")):
            self.assertEqual(_load_accounts_from_file(), [])

    def test_invalid_json_returns_empty(self):
        with open(self.token_file, "w") as f:
            f.write("not json")
        with patch("store.token.TOKEN_FILE", self.token_file):
            self.assertEqual(_load_accounts_from_file(), [])

    def test_non_dict_top_level_returns_empty(self):
        with open(self.token_file, "w") as f:
            json.dump([1, 2, 3], f)
        with patch("store.token.TOKEN_FILE", self.token_file):
            self.assertEqual(_load_accounts_from_file(), [])


class TestLoadAccounts(unittest.TestCase):
    def test_empty_scaffolds_file(self):
        tmpdir = tempfile.mkdtemp()
        token_file = os.path.join(tmpdir, "token.json")
        with patch("store.token.TOKEN_FILE", token_file), patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BOHE_ACCOUNTS", None)
            result = load_accounts()
        self.assertEqual(result, [])
        self.assertTrue(os.path.exists(token_file))


if __name__ == "__main__":
    unittest.main()
