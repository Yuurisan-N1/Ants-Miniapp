import os
import sys
import json
import time
import random
import signal
import asyncio
import aiohttp

from urllib.parse import parse_qs, unquote
from datetime import datetime, timezone

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Ants Miner Miniapp"

BASE_URL = "https://ap.antscoin.online"
FIRESTORE_API = ("https://firestore.googleapis.com/v1/projects/antsminers"
                 "/databases/(default)/documents")
IDENTITY_API = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"

FIREBASE_KEY = "AIzaSyApcFM_7vcnWVMUdTnJXIiG8wWlKKe5Q_M"

REF_CODE = "TBO2RF"

PROVIDERS = ("adsgram", "monetag", "richads", "premium", "adsgram_premium")

DAILY_LADDER = (1000, 2000, 3000, 5000, 8000, 13000, 21000)

CALL_ATTEMPTS = 3
CALL_RETRY_SECONDS = 4
ROUND_PAUSE_SECONDS = 2
RATE_LIMIT_PAUSE_SECONDS = 8
AD_PAUSE_SECONDS = 6
AD_SAFETY_ROUNDS = 15
NAME_LIMIT = 18
NOTE_LIMIT = 24
PROVIDER_LIMIT = 20

WHEEL_PAUSE_SECONDS = 720 * 60
WHEEL_PRIZES = (500, 1000, 2000, 3000, 5000, 10000)

TIMESTAMP_FIELDS = (
    "miningStartTime", "lastClaimTime", "lastWheelSpin", "lastCheckIn",
    "updatedAt", "timestamp",
)

TASKS = (
    ("tg_channel", 5000, "@ants_colony"),
    ("tg_channel2", 2500, "@AntsCoinPayout"),
    ("tg_group", 2500, "@ants_coin_community"),
    ("join_xrocket", 1500, "@xrocket"),
    ("join_blum", 1500, "@blum"),
    ("join_wallet", 1500, "@wallet"),
)

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

PAGE_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
)

LIMIT_WORDS = (
    "limit reached",
    "daily limit",
    "allowance",
)

ALREADY_WORDS = (
    "already claimed",
    "already referred",
    "already harvested",
    "no verified referral rewards",
)

JOIN_WORDS = (
    "not a member",
    "please join",
)


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def unit_word(value, singular, plural):
    try:
        return singular if int(value) == 1 else plural
    except Exception:
        return plural


def number_of(mapping, key, fallback=0):
    try:
        value = mapping.get(key)
    except Exception:
        return fallback
    if value is None or value == "":
        return fallback
    try:
        return int(float(value))
    except Exception:
        return fallback


def number_float(mapping, key, fallback=0.0):
    try:
        value = mapping.get(key)
    except Exception:
        return fallback
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except Exception:
        return fallback


def format_amount(value):
    try:
        number = float(value)
    except Exception:
        return "0"
    if number != number or number == 0:
        return "0"
    text = f"{number:.4f}" if abs(number) >= 1 else f"{number:.8f}"
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_payload(body):
    if not body:
        return {}
    stripped = body.strip()
    if not stripped.startswith("{"):
        return {}
    try:
        loaded = json.loads(stripped)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def api_error(payload):
    if isinstance(payload, dict):
        for key in ("error", "message"):
            if payload.get(key):
                return str(payload[key])
    return ""


def error_key(payload):
    return clean_text(api_error(payload), "").lower()


def matches(key, words):
    return any(word in key for word in words)


def load_config():
    defaults = {
        "settings": {
            "sleep_seconds": 3600,
        }
    }
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            loaded = json.load(handle)
    except Exception:
        return defaults
    settings = loaded.get("settings")
    if not isinstance(settings, dict):
        return defaults
    merged = dict(defaults["settings"])
    merged.update(settings)
    return {"settings": merged}


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines


def parse_init_data(line):
    value = line.strip()
    if "|" in value:
        value = value.rsplit("|", 1)[0].strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0].split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
        "lastName": str(profile.get("last_name") or ""),
        "startParam": str((fields.get("start_param") or [""])[0]),
        "token": "",
        "uid": "",
    }


def display_name(account):
    for candidate in (account.get("firstName"), account.get("username")):
        if candidate:
            return candidate
    return "account"


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def countdown(seconds, label):
    total = int(seconds)
    if total < 1:
        return
    line = ""
    for remaining in range(total, 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        line = f"{clean_text(label, 'item')} {hours:02d}:{minutes:02d}:{rest:02d}"
        print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * (len(line) + 6) + "\r", end="", flush=True)


async def call_json(session, method, url, proxy, payload, token):
    last_status = 0
    last_body = ""
    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": BASE_URL,
        "referer": BASE_URL + "/",
        "user-agent": PAGE_AGENT,
    }
    if token:
        headers["authorization"] = "Bearer " + token
    if payload is not None:
        headers["content-type"] = "application/json"
    for attempt in range(1, CALL_ATTEMPTS + 1):
        pause = CALL_RETRY_SECONDS * attempt
        body_text = json.dumps(payload) if payload is not None else None
        try:
            request = session.request(
                method,
                url,
                data=body_text,
                headers=headers,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=40),
            )
            async with request as response:
                last_status = response.status
                last_body = await response.text()
                if response.status < 500 and response.status != 429:
                    return last_status, last_body
                if response.status == 429:
                    pause = RATE_LIMIT_PAUSE_SECONDS * attempt
        except Exception:
            last_status = 0
            last_body = ""
        if attempt < CALL_ATTEMPTS:
            countdown(pause, "Retry in")
    return last_status, last_body


async def sign_in(session, proxy, account):
    status, body = await call_json(
        session, "POST", BASE_URL + "/api/telegram-auth", proxy,
        {
            "initData": account["initData"],
            "referralCode": REF_CODE,
            "start_param": REF_CODE,
        }, "")
    payload = parse_payload(body)
    custom = payload.get("token")
    if status != 200 or not custom:
        return False
    status, body = await call_json(
        session, "POST", f"{IDENTITY_API}?key={FIREBASE_KEY}", proxy,
        {"token": custom, "returnSecureToken": True}, "")
    payload = parse_payload(body)
    account["token"] = payload.get("idToken") or ""
    account["uid"] = payload.get("localId") or ""
    if not account["token"]:
        return False
    if not account["uid"]:
        account["uid"] = "telegram_" + account["id"]
    return True


def firestore_body(fields):
    converted = {}
    for key, value in fields.items():
        if isinstance(value, bool):
            converted[key] = {"booleanValue": value}
        elif isinstance(value, int):
            converted[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            converted[key] = {"doubleValue": value}
        elif isinstance(value, (list, tuple)):
            converted[key] = {"arrayValue": {
                "values": [{"stringValue": str(item)} for item in value]}}
        elif key in TIMESTAMP_FIELDS and isinstance(value, str):
            converted[key] = {"timestampValue": value}
        else:
            converted[key] = {"stringValue": str(value)}
    return {"fields": converted}


def firestore_read(fields):
    loaded = {}
    if not isinstance(fields, dict):
        return loaded
    for key, value in fields.items():
        if not isinstance(value, dict):
            continue
        for kind, raw in value.items():
            if kind == "integerValue":
                try:
                    loaded[key] = int(str(raw))
                except Exception:
                    loaded[key] = 0
            elif kind == "doubleValue":
                try:
                    loaded[key] = float(raw)
                except Exception:
                    loaded[key] = 0
            elif kind == "arrayValue":
                listed = []
                for item in (raw or {}).get("values", []):
                    if isinstance(item, dict):
                        listed.append(str(item.get("stringValue") or
                                          item.get("integerValue") or ""))
                loaded[key] = listed
            elif kind in ("stringValue", "timestampValue"):
                loaded[key] = str(raw)
            elif kind == "booleanValue":
                loaded[key] = bool(raw)
    return loaded


async def firestore_get(session, proxy, account, path):
    url = f"{FIRESTORE_API}/{path}"
    status, body = await call_json(session, "GET", url, proxy, None, account["token"])
    payload = parse_payload(body)
    return firestore_read(payload.get("fields"))


async def firestore_write(session, proxy, account, path, fields):
    mask = "&".join(f"updateMask.fieldPaths={key}" for key in fields)
    url = f"{FIRESTORE_API}/{path}?updateMask.fieldPaths=updatedAt&{mask}"
    status, body = await call_json(
        session, "PATCH", url, proxy, firestore_body(fields), account["token"])
    return status == 200


def stamp_now():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def day_of(value):
    if isinstance(value, int):
        if value <= 0:
            return ""
        moment = datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
        return moment.strftime("%Y-%m-%d")
    if not value or not isinstance(value, str):
        return ""
    return value[:10]


def moment_of(value):
    if isinstance(value, int):
        return float(value) / 1000.0
    if not value or not isinstance(value, str):
        return 0.0
    text = value.replace("Z", "").split(".")[0]
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return 0.0
    return parsed.replace(tzinfo=timezone.utc).timestamp()


def next_streak(last_day, streak):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not last_day or last_day.startswith("1970"):
        return 1
    if last_day == today:
        return 0
    try:
        previous = datetime.strptime(last_day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        gap = (datetime.now(timezone.utc) - previous).days
    except Exception:
        return 1
    if gap != 1:
        return 1
    streak = streak + 1
    return 1 if streak > len(DAILY_LADDER) else streak


async def run_daily(session, proxy, account, state):
    user = await firestore_get(session, proxy, account, "users/" + account["uid"])
    if not user:
        log_red("Daily protocol state could not be read from the server")
        return
    streak = number_of(user, "currentStreak", 0)
    day = next_streak(day_of(user.get("lastCheckIn")), streak)
    if day < 1:
        log_yellow("The daily protocol reward was already collected today")
        return
    amount = DAILY_LADDER[day - 1]
    before = number_float(user, "balance", 0.0)
    moment = stamp_now()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written = await firestore_write(
        session, proxy, account, "users/" + account["uid"],
        {
            "balance": before + float(amount),
            "currentStreak": day,
            "lastCheckIn": moment,
            "updatedAt": moment,
        })
    if not written:
        log_red("The daily protocol reward was refused by the server")
        return
    await firestore_write(
        session, proxy, account,
        f"users/{account['uid']}/activity/task/transactions/daily_{account['uid']}_{today}",
        {
            "userId": account["uid"],
            "amount": amount,
            "type": "daily_reward",
            "status": "completed",
            "timestamp": moment,
        })
    fresh = await firestore_get(session, proxy, account, "users/" + account["uid"])
    credited = number_float(fresh, "balance", before) - before
    if credited > 0:
        state["balance"] = before + credited
        log_green(f"Daily protocol reward credited "
                  f"{clean_text(format_amount(credited), 0)} ANTS")
    else:
        log_yellow("The daily protocol reward was not confirmed by the server")


async def run_community(session, proxy, account, state):
    status, body = await call_json(
        session, "POST", BASE_URL + "/api/verify-community-status", proxy,
        {"telegramId": number_of(account, "id", 0)}, account["token"])
    payload = parse_payload(body)
    if status != 200 or not payload.get("success"):
        log_red("Community membership could not be checked with the server")
        return
    if payload.get("isFullyVerified"):
        log_green("Community membership is verified on this account")
        return
    if payload.get("isChannelMember") or payload.get("isChannel2Member"):
        log_yellow("Community membership still needs a real group join")
        return
    log_yellow("Community membership still needs a real channel join")


async def run_ads(session, proxy, account, state):
    credited = 0
    exhausted = 0
    for provider in PROVIDERS:
        label = clean_text(provider, "provider")
        for _ in range(AD_SAFETY_ROUNDS):
            status, body = await call_json(
                session, "POST", BASE_URL + "/api/watch-ad", proxy,
                {"provider": provider, "userId": account["uid"]}, account["token"])
            payload = parse_payload(body)
            if status == 200 and payload.get("success"):
                amount = number_of(payload, "reward", 0)
                state["balance"] = number_of(payload, "newBalance",
                                             state.get("balance", 0))
                credited += amount
                log_green(f"Ad reward credited {clean_text(amount, 0)} ANTS")
                await asyncio.sleep(AD_PAUSE_SECONDS)
                continue
            key = error_key(payload)
            if matches(key, LIMIT_WORDS):
                exhausted += 1
                break
            note = shorten(api_error(payload), "the server refused the claim", NOTE_LIMIT)
            log_red(f"Ad reward failed because {clean_text(note, 'refused')}")
            break
    if credited <= 0:
        log_yellow("No ad reward was available on this run")
    if exhausted:
        log_yellow(f"Ad allowance was used up for {clean_text(exhausted, 0)} "
                   f"{unit_word(exhausted, 'provider', 'providers')}")


async def run_vault(session, proxy, account, state):
    status, body = await call_json(
        session, "POST",
        BASE_URL + "/api/claim-rewards?action=vault_status&userId=" + account["uid"],
        proxy, {"action": "vault_status", "userId": account["uid"]}, account["token"])
    payload = parse_payload(body)
    if status != 200 or not payload.get("success"):
        return
    claimable = number_of(payload, "claimableAmount", 0)
    if claimable <= 0:
        log_yellow("The referral vault holds no reward to unlock yet")
        return
    status, body = await call_json(
        session, "POST", BASE_URL + "/api/claim-rewards?action=claim_vault",
        proxy, {"action": "claim_vault"}, account["token"])
    payload = parse_payload(body)
    if status == 200 and payload.get("success"):
        claimed = number_of(payload, "claimed", claimable)
        state["balance"] = number_of(payload, "newBalance", state.get("balance", 0))
        log_green(f"Referral vault credited {clean_text(claimed, 0)} ANTS")
        return
    key = error_key(payload)
    if matches(key, ALREADY_WORDS):
        log_yellow("The referral vault was already unlocked")
        return
    note = shorten(api_error(payload), "the server refused it", NOTE_LIMIT)
    log_red(f"Referral vault refused because {clean_text(note, 'refused')}")


async def start_engine(session, proxy, account):
    moment = stamp_now()
    written = await firestore_write(
        session, proxy, account, "users/" + account["uid"],
        {
            "miningStartTime": moment,
            "lastClaimTime": moment,
            "updatedAt": moment,
        })
    if not written:
        log_red("The mining engine could not be started on this account")
        return
    await firestore_write(
        session, proxy, account,
        f"users/{account['uid']}/activity/mining_start",
        {
            "userId": account["uid"],
            "amount": 0,
            "type": "mining_start",
            "status": "completed",
            "timestamp": moment,
        })
    log_yellow("The mining engine was started for the next cycle")


async def run_claim(session, proxy, account, state):
    user = await firestore_get(session, proxy, account, "users/" + account["uid"])
    if not user:
        log_red("The mining state could not be read from the server")
        return
    before = number_float(user, "balance", 0.0)
    if user.get("miningStartTime"):
        status, body = await call_json(
            session, "POST", BASE_URL + "/api/claim-rewards", proxy, None,
            account["token"])
        payload = parse_payload(body)
        if status == 200 and payload.get("success"):
            credited = number_float(payload, "reward", 0.0)
            if credited <= 0:
                fresh = await firestore_get(session, proxy, account,
                                            "users/" + account["uid"])
                credited = number_float(fresh, "balance", before) - before
            if credited > 0:
                state["balance"] = before + credited
                log_green(f"Mining claim credited "
                          f"{clean_text(format_amount(credited), 0)} ANTS")
            else:
                log_yellow("The mining claim returned no confirmed credit")
        else:
            key = error_key(payload)
            if matches(key, ALREADY_WORDS):
                log_yellow("The mining claim was already collected")
            else:
                note = shorten(api_error(payload), "the server refused it", NOTE_LIMIT)
                log_red(f"Mining claim failed because {clean_text(note, 'refused')}")
    else:
        log_yellow("The mining engine was idle on this account")
    fresh = await firestore_get(session, proxy, account, "users/" + account["uid"])
    if fresh and not fresh.get("miningStartTime"):
        await start_engine(session, proxy, account)


async def run_wheel(session, proxy, account, state):
    user = await firestore_get(session, proxy, account, "users/" + account["uid"])
    if not user:
        log_red("The wheel state could not be read from the server")
        return
    last = moment_of(user.get("lastWheelSpin"))
    if last > 0 and time.time() - last < WHEEL_PAUSE_SECONDS:
        log_yellow("The lucky wheel is still cooling down on this account")
        return
    before = number_float(user, "balance", 0.0)
    prize = random.choice(WHEEL_PRIZES)
    moment = stamp_now()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written = await firestore_write(
        session, proxy, account, "users/" + account["uid"],
        {
            "balance": before + float(prize),
            "lastWheelSpin": moment,
            "updatedAt": moment,
        })
    if not written:
        log_red("The lucky wheel spin was refused by the server")
        return
    await firestore_write(
        session, proxy, account,
        f"users/{account['uid']}/activity/task/transactions/wheel_"
        f"{account['uid']}_{today}",
        {
            "userId": account["uid"],
            "amount": prize,
            "type": "wheel_win",
            "status": "completed",
            "timestamp": moment,
        })
    fresh = await firestore_get(session, proxy, account, "users/" + account["uid"])
    credited = number_float(fresh, "balance", before) - before
    if credited > 0:
        state["balance"] = before + credited
        log_green(f"Lucky wheel credited "
                  f"{clean_text(format_amount(credited), 0)} ANTS")
    else:
        log_yellow("The lucky wheel returned no confirmed credit")


async def run_tasks(session, proxy, account, state):
    user = await firestore_get(session, proxy, account, "users/" + account["uid"])
    if not user:
        log_red("The task state could not be read from the server")
        return
    done = [str(item) for item in (user.get("completedTasks") or [])]
    activity = await firestore_get(session, proxy, account,
                                   f"users/{account['uid']}/activity/task")
    for item in (activity.get("completedTasks") or []):
        if str(item) not in done:
            done.append(str(item))
    pending = [task for task in TASKS if task[0] not in done]
    if not pending:
        log_yellow("Every available account task was already completed")
        return
    for task_id, reward, chat in pending:
        status, body = await call_json(
            session, "POST", BASE_URL + "/api/verify-telegram", proxy,
            {"chatId": chat, "telegramId": number_of(account, "id", 0)},
            account["token"])
        payload = parse_payload(body)
        if status != 200 or not payload.get("success") or not payload.get("isAllowed"):
            log_yellow(f"Account task {clean_text(task_id, 'task')} still needs "
                       f"a real join")
            continue
        before = number_float(user, "balance", 0.0)
        moment = stamp_now()
        done.append(task_id)
        written = await firestore_write(
            session, proxy, account, "users/" + account["uid"],
            {
                "balance": before + float(reward),
                "updatedAt": moment,
            })
        if written:
            written = await firestore_write(
                session, proxy, account,
                f"users/{account['uid']}/activity/task",
                {"completedTasks": done})
        if not written:
            log_red(f"Account task {clean_text(task_id, 'task')} reward was "
                    f"refused by the server")
            continue
        await firestore_write(
            session, proxy, account,
            f"users/{account['uid']}/activity/task/transactions/"
            f"task_{account['uid']}_{task_id}",
            {
                "userId": account["uid"],
                "amount": reward,
                "type": "task_reward",
                "status": "completed",
                "timestamp": moment,
                "taskId": task_id,
            })
        fresh = await firestore_get(session, proxy, account, "users/" + account["uid"])
        credited = number_float(fresh, "balance", before) - before
        if credited > 0:
            user = fresh
            state["balance"] = before + credited
            log_green(f"Account task {clean_text(task_id, 'task')} credited "
                      f"{clean_text(format_amount(credited), 0)} ANTS")
        else:
            log_yellow(f"Account task {clean_text(task_id, 'task')} returned "
                       f"no confirmed credit")


async def process_account(line, proxy, index):
    account = parse_init_data(line)
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        if not await sign_in(session, proxy, account):
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        state = await firestore_get(session, proxy, account, "users/" + account["uid"])
        if not state:
            log_red(f"Account state could not be read for account number "
                    f"{clean_text(index, 1)}")
            return

        name = shorten(display_name(account), "account", NAME_LIMIT)
        balance = number_float(state, "balance", 0.0)
        log_green(f"Signed in {clean_text(name, 'account')} with "
                  f"{clean_text(format_amount(balance), 0)} ANTS")

        await run_claim(session, proxy, account, state)
        await run_wheel(session, proxy, account, state)
        await run_daily(session, proxy, account, state)
        await run_community(session, proxy, account, state)
        await run_tasks(session, proxy, account, state)
        await run_ads(session, proxy, account, state)
        await run_vault(session, proxy, account, state)

        closing = await firestore_get(session, proxy, account, "users/" + account["uid"])
        if closing:
            balance = number_float(closing, "balance", balance)
        log_yellow(f"Closing balance on this account "
                   f"{clean_text(format_amount(balance), 0)} ANTS")


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1)
            countdown(ROUND_PAUSE_SECONDS, "Next account in")

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = load_config().get("settings", {})
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, settings["sleep_seconds"]))


if __name__ == "__main__":
    main()
