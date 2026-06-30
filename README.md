# bohe-api-auto-signin

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-Modified_MIT-red.svg)

> Automation solution for Bohe Public Welfare Station (up.x666.me) daily signin and lucky draw.

---

> [!IMPORTANT]
> In addition to the standard MIT license, you must also comply with the following: This project is strictly prohibited
> from being used for any form of commercial behavior. It is strictly forbidden to integrate it into paid platforms or
> paid automated services.

---

## Credential Acquisition

Only `bohe_session_cookies` is needed. The OAuth refresh flow (which previously auto-obtained session cookies from a
`linux_do_token`) has been removed — when the session expires you update the cookie manually.

### `bohe_session_cookies`

* **Source**: HttpOnly `auth_token` cookie set by `up.x666.me` after the Linux.do OAuth callback.
* **How to get**: Complete the Linux.do OAuth login on `up.x666.me` in a browser, then open Developer Tools (F12) ->
  Application -> Cookies -> `https://up.x666.me` and copy the value of `auth_token`.
* **Note**: The old LocalStorage token flow is no longer used by the current frontend API. The program only verifies
  this cookie against `/api/user/info`; it does not attempt to refresh it. Update it manually when it expires.

---

## Multi-Account Configuration

Multiple accounts are configured through a single `BOHE_ACCOUNTS` value (a GitHub secret in CI, or an environment
variable locally) containing a JSON array. Each entry needs a `bohe_session_cookies`:

```json
[
  {
    "bohe_session_cookies": "xxxx"
  },
  {
    "bohe_session_cookies": "yyyy"
  }
]
```

Set it as a single-line secret/env value, for example:

```bash
BOHE_ACCOUNTS='[{"bohe_session_cookies":"xxxx"},{"bohe_session_cookies":"yyyy"}]'
```

Accounts are processed sequentially (with a short randomized delay between them) to stay within the shared Bohe rate
limits.

### Account storage

The roster has exactly two sources, in priority order:

1. The `BOHE_ACCOUNTS` JSON env var / secret.
2. The `accounts` array in `.data/token.json`.

If nothing is configured, the program scaffolds an empty `accounts` array in `.data/token.json` for you to fill in.
Tokens are **not** written back after a run — update `.data/token.json` / the `BOHE_ACCOUNTS` secret manually when a
session expires.

### Migration from the OAuth version

The legacy `linux_do_token` / `linux_do_connect_token` fields are ignored (configs carrying them still parse). To
migrate:

* **Local `.data/token.json`** — replace the account entries with just `bohe_session_cookies`:

  ```json
  { "accounts": [ { "bohe_session_cookies": "..." } ] }
  ```

* **Environment / CI** — set `BOHE_ACCOUNTS` to a JSON array of `{"bohe_session_cookies": "..."}` objects and remove
  the old `LINUX_DO_TOKEN` / `LINUX_DO_CONNECT_TOKEN` secrets.
