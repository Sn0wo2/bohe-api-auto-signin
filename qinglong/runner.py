import os
import sys

# Stable cwd + import path so `import main` works and ./.data stays put,
# however QingLong launches the task. Override token location with BOHE_DATA_DIR.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import asyncio  # noqa: E402
import io  # noqa: E402
import logging  # noqa: E402
import re  # noqa: E402

import main  # noqa: E402

_LOGGER = "bohe-api-auto-signin"


def _enabled() -> bool:
    flag = os.getenv("BOHE_QL_NOTIFY", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("QL_DIR") or os.getenv("QL_BRANCH")) or os.path.isdir("/ql")


def _push(title: str, content: str) -> None:
    """Send via QingLong's notify.send; best-effort, never raises."""
    try:
        from notify import send
    except Exception:
        sys.path.append(os.path.join(os.getenv("QL_DIR", "/ql"), "scripts"))
        try:
            from notify import send
        except Exception:
            return
    try:
        send(title, content)
    except Exception:
        pass


def run() -> int:
    notify = _enabled()
    buf = io.StringIO()
    if notify:
        # main.py configures the logger at import; attach AFTER so it stays intact.
        handler = logging.StreamHandler(buf)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
        )
        logging.getLogger(_LOGGER).addHandler(handler)

    code = 0
    try:
        asyncio.run(main.main())
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:
        logging.getLogger(_LOGGER).exception("Signin run crashed")
        code = 1

    if notify:
        log = buf.getvalue() or "(no log output)"
        m = re.search(r"Done:\s*(\d+)\s+succeeded,\s*(\d+)\s+failed", log)
        title = (
            f"🌿 薄荷签到 ✅{m.group(1)} ❌{m.group(2)}"
            if m
            else "🌿 薄荷签到完成" if code == 0 else "🌿 薄荷签到 ❌"
        )
        _push(title, log)

    return code


if __name__ == "__main__":
    sys.exit(run())
