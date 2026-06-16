import json
import os
from dataclasses import dataclass

from utils.paths import DATA_DIR

TOKEN_FILE = os.path.join(DATA_DIR, "token.json")

_TOKEN_KEYS = (
    "bohe_session_cookies",
    "linux_do_connect_token",
    "linux_do_token",
)


@dataclass
class Account:
    name: str = "default"
    bohe_session_cookies: str = ""
    linux_do_connect_token: str = ""
    linux_do_token: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, **{key: getattr(self, key) for key in _TOKEN_KEYS}}


def _str(value: object) -> str:
    return value if isinstance(value, str) and value else ""


def _parse_account(raw: dict, default_name: str) -> Account:
    return Account(
        name=_str(raw.get("name")) or default_name,
        **{key: _str(raw.get(key)) for key in _TOKEN_KEYS},
    )


def _parse_roster(items: object) -> list[Account]:
    if not isinstance(items, list):
        return []
    return [
        _parse_account(item, f"account{i + 1}")
        for i, item in enumerate(items)
        if isinstance(item, dict)
    ]


def _accounts_from_env() -> list[Account] | None:
    raw = os.getenv("BOHE_ACCOUNTS")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    accounts = _parse_roster(data)
    return accounts or None


def _accounts_from_file() -> list[Account]:
    if not os.path.exists(TOKEN_FILE):
        return []
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, dict):
        return []
    return _parse_roster(raw.get("accounts"))


def _write_accounts(accounts: list[Account]) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)
    payload = {"accounts": [account.to_dict() for account in accounts]}
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def load_accounts() -> list[Account]:
    """Resolve the account roster from the BOHE_ACCOUNTS JSON env var,
    falling back to the token file's `accounts` array."""
    env_accounts = _accounts_from_env()
    if env_accounts is not None:
        return env_accounts

    accounts = _accounts_from_file()
    if not accounts:
        # Nothing configured yet: scaffold an empty token file so the
        # expected `accounts` shape is discoverable.
        _write_accounts([])
    return accounts


def save_accounts(accounts: list[Account]) -> None:
    """Persist the full account roster to the token file."""
    _write_accounts(accounts)
