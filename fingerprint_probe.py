import asyncio
import os
from typing import get_args

from curl_cffi import requests
from curl_cffi.requests.session import BrowserTypeLiteral
from linux_do_connect import LinuxDoConnect, CONNECT_KEY

FINGERPRINTS = list(get_args(BrowserTypeLiteral))


async def test():
    token = os.getenv('LINUX_DO_TOKEN')
    async with requests.AsyncSession() as s:
        r = await s.get('https://up.x666.me/api/auth/login', impersonate='chrome136')
        auth_url = r.json()['auth_url']
    c = LinuxDoConnect(token)
    await c.login()
    connect_token = c.session.cookies.get(CONNECT_KEY, domain='connect.linux.do')
    results = []
    for fp in FINGERPRINTS:
        bare_ok = False
        authed_ok = False
        status_code = 0
        try:
            async with requests.AsyncSession() as s:
                r = await s.get(auth_url, impersonate=fp, timeout=10)
                bare_ok = r.status_code == 200 and 'Just a moment' not in r.text
        except Exception:
            pass
        try:
            c2 = LinuxDoConnect()
            c2.set_connect_token(connect_token)
            r = await c2.session.get(auth_url, impersonate=fp, timeout=10)
            authed_ok = r.status_code == 200 and 'Just a moment' not in r.text
            status_code = r.status_code
        except Exception:
            pass
        bare_str = 'OK' if bare_ok else 'X'
        authed_str = 'OK' if authed_ok else 'X'
        if bare_ok or authed_ok:
            results.append((fp, bare_str, authed_str))
        print(f'{fp:22s} bare={bare_str}  authed={authed_str}  status={status_code}')
    print()
    print('=' * 25)
    for fp, bare_label, authed_label in results:
        print(f'  {fp:22s} bare={bare_label}  authed={authed_label}')


asyncio.run(test())
