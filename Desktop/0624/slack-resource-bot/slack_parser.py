from datetime import datetime, timezone, timedelta
from typing import Optional
from slack_sdk import WebClient

KST = timezone(timedelta(hours=9))

LOCATION_KEYWORDS = {
    "전야재": ("전야재", True),
    "오전재택": ("재택", False),
    "재택": ("재택", False),
    "사무실": ("사무실", False),
}

WORKFLOW_KEYWORDS = {
    "checkin": ["출근 기록", "출근기록"],
    "lunch": ["점심 기록", "점심기록"],
    "checkout": ["퇴근 기록", "퇴근기록"],
}


def parse_location(text: str) -> tuple[str, bool]:
    # 전야재 먼저 체크 (오전재택보다 우선)
    for keyword in ["전야재", "오전재택", "재택", "사무실"]:
        if keyword in text:
            return LOCATION_KEYWORDS[keyword]
    return ("사무실", False)


def find_workflow_threads(messages: list[dict]) -> dict[str, Optional[str]]:
    result = {"checkin": None, "lunch": None, "checkout": None}
    for msg in messages:
        if msg.get("reply_count", 0) == 0:
            continue
        text = msg.get("text", "")
        for thread_type, keywords in WORKFLOW_KEYWORDS.items():
            if result[thread_type] is None:
                for kw in keywords:
                    if kw in text:
                        result[thread_type] = msg["ts"]
                        break
    return result


def extract_user_records(replies: list[dict]) -> dict[str, dict]:
    records = {}
    for reply in replies:
        if "bot_id" in reply:
            continue
        user = reply.get("user")
        if user and user not in records:
            records[user] = reply
    return records


def ts_to_kst_datetime(ts: str) -> datetime:
    return datetime.fromtimestamp(float(ts), tz=KST)


def get_display_name(client: WebClient, user_id: str) -> str:
    resp = client.users_info(user=user_id)
    profile = resp["user"]["profile"]
    return profile.get("display_name") or profile.get("real_name", user_id)


def fetch_day_records(client: WebClient, channel_id: str, target_date: datetime) -> list[dict]:
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    oldest = str(day_start.timestamp())
    latest = str(day_end.timestamp())

    resp = client.conversations_history(
        channel=channel_id, oldest=oldest, latest=latest, limit=200
    )
    messages = resp.get("messages", [])

    threads = find_workflow_threads(messages)

    records_by_user: dict[str, dict] = {}

    for thread_type, thread_ts in threads.items():
        if thread_ts is None:
            continue
        replies_resp = client.conversations_replies(channel=channel_id, ts=thread_ts, limit=200)
        replies = replies_resp.get("messages", [])[1:]  # skip parent
        user_records = extract_user_records(replies)
        for user_id, reply in user_records.items():
            if user_id not in records_by_user:
                records_by_user[user_id] = {}
            records_by_user[user_id][thread_type] = reply

    results = []
    for user_id, data in records_by_user.items():
        checkin_reply = data.get("checkin")
        lunch_reply = data.get("lunch")
        checkout_reply = data.get("checkout")

        checkin_ts = ts_to_kst_datetime(checkin_reply["ts"]) if checkin_reply else None
        lunch_ts = ts_to_kst_datetime(lunch_reply["ts"]) if lunch_reply else None
        checkout_ts = ts_to_kst_datetime(checkout_reply["ts"]) if checkout_reply else None

        location, is_jeonya = parse_location(checkin_reply["text"]) if checkin_reply else ("미분류", False)

        display_name = get_display_name(client, user_id)

        results.append({
            "user_id": user_id,
            "display_name": display_name,
            "checkin_ts": checkin_ts,
            "lunch_ts": lunch_ts,
            "checkout_ts": checkout_ts,
            "location": location,
            "is_jeonya": is_jeonya,
        })

    return results
