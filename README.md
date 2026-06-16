# bohe-api-auto-signin

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-Modified_MIT-red.svg)

> Automation solution for Bohe Public Welfare Station (up.x666.me) daily signin and lucky draw.

---

> [!IMPORTANT]
> In addition to the standard MIT license, you must also comply with the following: This project is strictly prohibited from being used for any form of commercial behavior. It is strictly forbidden to integrate it into paid platforms or paid automated services.

---

## Credential Acquisition

Provide `linux_do_token` and let the program complete OAuth, verify the Bohe session, and persist `bohe_session_cookies` automatically.

### 1. `linux_do_token`

*   **Source**: Session persistence cookie from the `linux.do` site.
*   **How to get**: After logging in to `linux.do`, find the value of `_t` in Developer Tools (F12) -> Application -> Cookies.
*   **Note**: This is the recommended credential because it can refresh the connect token and Bohe session cookies automatically.

### 2. `linux_do_connect_token`

*   **Source**: Connection credential from the `connect.linux.do` authorization center.
*   **How to get**: After logging in to `linux.do`, find the value of `auth.session-token` in Developer Tools (F12) -> Application -> Cookies.
*   **Note**: Providing only this token can refresh the Bohe session until the connect token expires. `linux_do_token` is still recommended for unattended runs.

### 3. `bohe_session_cookies`

*   **Source**: HttpOnly cookies set by `up.x666.me` after the Linux.do OAuth callback.
*   **How to get**: Normally you do not need to get them manually. The program stores them in `.data/token.json` after a successful OAuth flow.
*   **Note**: The old LocalStorage token flow is no longer used by the current frontend API.

---

## Multi-Account Configuration

Multiple accounts are configured through a single `BOHE_ACCOUNTS` value (a GitHub secret in CI, or an environment variable locally) containing a JSON array. Each entry needs at least a `name` and a `linux_do_token`; the program fills in `linux_do_connect_token` and `bohe_session_cookies` automatically after a successful run.

```json
[
  { "name": "acc1", "linux_do_token": "xxxx" },
  { "name": "acc2", "linux_do_token": "yyyy" }
]
```

Set it as a single-line secret/env value, for example:

```bash
BOHE_ACCOUNTS='[{"name":"acc1","linux_do_token":"xxxx"},{"name":"acc2","linux_do_token":"yyyy"}]'
```

Accounts are processed sequentially (with a short randomized delay between them) to stay within the shared linux.do / Bohe rate limits.

### Token persistence

The roster has exactly two sources, in priority order:

1.  The `BOHE_ACCOUNTS` JSON env var / secret.
2.  The `accounts` array in `.data/token.json`.

*   Locally, the refreshed roster is written back to `.data/token.json` under the `accounts` array.
*   In GitHub Actions, the workflow reads `.data/token.json` after the run and writes the refreshed roster back to the `BOHE_ACCOUNTS` secret (and to any repositories listed in `SYNC_REPOS`).

### Migration from the single-account version

The legacy single-account variables (`LINUX_DO_TOKEN`, `LINUX_DO_CONNECT_TOKEN`, `BOHE_SESSION_COOKIES`) and the old flat `token.json` shape are **no longer supported**. To migrate:

*   **Local `.data/token.json`** — wrap your existing flat object in an `accounts` array and give it a `name`:

    ```json
    { "accounts": [ { "name": "default", "linux_do_token": "xxxx", "linux_do_connect_token": "...", "bohe_session_cookies": "..." } ] }
    ```

*   **Environment / CI** — set a single `BOHE_ACCOUNTS` secret (JSON array) as shown above and remove the old `LINUX_DO_TOKEN` / `LINUX_DO_CONNECT_TOKEN` / `BOHE_SESSION_COOKIES` secrets.

If nothing is configured, the program scaffolds an empty `accounts` array in `.data/token.json` for you to fill in.
