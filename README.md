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
