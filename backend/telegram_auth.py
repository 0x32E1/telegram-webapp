"""
Verifies the `initData` string a Telegram Mini App sends with every request,
per https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

initData is a query-string like:
  user=%7B%22id%22%3A123...%7D&auth_date=1699999999&hash=abcd...

We recompute the HMAC over every field except `hash` and compare it to the
`hash` field. If they don't match, the request didn't really come from
Telegram (or was tampered with) and must be rejected.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import config


class InitDataError(Exception):
    pass


def verify_init_data(init_data: str, max_age_seconds: int = 86400) -> dict:
    """Returns the parsed Telegram user dict on success, raises InitDataError otherwise."""
    if config.DEV_MODE:
        # Local design-review shortcut only — never used when DEV_MODE is off.
        return {"id": 111111111, "username": "demo_user", "first_name": "Demo", "last_name": "User"}

    if not init_data:
        raise InitDataError("Missing initData")

    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("Invalid signature")

    auth_date = int(pairs.get("auth_date", 0))
    if time.time() - auth_date > max_age_seconds:
        raise InitDataError("initData expired")

    user_json = pairs.get("user")
    if not user_json:
        raise InitDataError("Missing user")

    return json.loads(user_json)
