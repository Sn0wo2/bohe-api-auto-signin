import json
import os
from venv import logger
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from utils.paths import DATA_DIR

TOKEN_FILE = os.path.join(DATA_DIR, "token.json")


class Account(BaseModel):
    bohe_session_cookies: str = Field(default="", description="Bohe session cookies")

    # extra="ignore" so legacy configs still carrying the removed linux_do_*
    # fields parse without error instead of crashing on startup.
    model_config = {
        "extra": "ignore",
        "str_strip_whitespace": True,
    }


AccountListAdapter = TypeAdapter(list[Account])


def _parse_roster(items: object) -> list[Account]:
    try:
        return AccountListAdapter.validate_python(items)
    except ValidationError as e:
        logger.exception(f"failed to parse account roster: {e}")
        return []


def _load_accounts_from_env() -> list[Account] | None:
    raw = os.getenv("BOHE_ACCOUNTS")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return _parse_roster(data) or None


def _load_accounts_from_file() -> list[Account]:
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(raw, dict):
        return []

    return _parse_roster(raw.get("accounts"))


def _write_accounts_to_file(accounts: list[Account]) -> None:
    os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)

    payload = {"accounts": [account.model_dump() for account in accounts]}

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def load_accounts() -> list[Account]:
    accounts = []

    file_accounts = _load_accounts_from_file()
    accounts.extend(file_accounts)

    env_accounts = _load_accounts_from_env()
    if env_accounts is not None:
        accounts.extend(env_accounts)

    if not accounts:
        _write_accounts_to_file([])

    return accounts
