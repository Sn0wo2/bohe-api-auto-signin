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

    def has_credentials(self) -> bool:
        return any(getattr(self, key) for key in _TOKEN_KEYS)


def _str(value: object) -> str:
    return value if isinstance(value, str) and value else ""


def _parse_account(raw: dict, default_name: str) -> Account:
    return Account(
        name=_str(raw.get("name")) or default_name,
        **{key: _str(raw.get(key)) for key in _TOKEN_KEYS},
    )


def _accounts_from_env() -> list[Account] | None:
    raw = os.getenv("BOHE_ACCOUNTS")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    accounts = [
        _parse_account(item, f"account{i + 1}")
        for i, item in enumerate(data)
        if isinstance(item, dict)
    ]
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

    if isinstance(raw.get("accounts"), list):
        return [
            _parse_account(item, f"account{i + 1}")
            for i, item in enumerate(raw["accounts"])
            if isinstance(item, dict)
        ]

    # Legacy single-account shape: tokens stored as top-level keys.
    account = _parse_account(raw, "default")
    return [account] if account.has_credentials() else []


def _apply_legacy_env(account: Account) -> None:
    env_cookies = os.getenv("BOHE_SESSION_COOKIES")
    if env_cookies:
        account.bohe_session_cookies = env_cookies
    env_connect = os.getenv("LINUX_DO_CONNECT_TOKEN")
    if env_connect:
        account.linux_do_connect_token = env_connect
    env_ld = os.getenv("LINUX_DO_TOKEN")
    if env_ld:
        account.linux_do_token = env_ld


def _write_accounts(accounts: list[Account]) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)
    payload = {"accounts": [account.to_dict() for account in accounts]}
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def load_accounts() -> list[Account]:
    """Resolve the account roster, in priority order, from the BOHE_ACCOUNTS
    JSON env var, the token file, or the legacy single-account env vars."""
    env_accounts = _accounts_from_env()
    if env_accounts is not None:
        return env_accounts

    accounts = _accounts_from_file()
    if not accounts:
        # No roster yet: fall back to the legacy single-account env vars so
        # existing setups keep working, and scaffold an empty token file.
        account = Account(name="default")
        _apply_legacy_env(account)
        accounts = [account]
        _write_accounts(accounts)
        return accounts

    # Preserve legacy behaviour: a lone account can still be overridden by env.
    if len(accounts) == 1:
        _apply_legacy_env(accounts[0])
    return accounts


def save_accounts(accounts: list[Account]) -> None:
    """Persist the full account roster to the token file."""
    _write_accounts(accounts)
