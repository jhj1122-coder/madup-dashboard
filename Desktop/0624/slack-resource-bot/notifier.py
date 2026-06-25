from datetime import datetime
from typing import Optional
from slack_sdk import WebClient


def build_special_leave_msg(date_str: str, location: str, work_hours: float, case: str) -> str:
    if case == "CASE1":
        condition = f"CASE1 조건 충족 (15시간 이상 사무실 근무)"
    else:
        condition = f"CASE2 조건 충족 (전야재 + 11시간 이상 근무)"

    return (
        f"🎁 어제({date_str}) 특별휴가가 발생했어요!\n"
        f"📍 위치: {location} | ⏱ 업무시간: {work_hours}시간\n"
        f"{condition}\n"
        f"특별휴가 신청은 HR에 문의해주세요."
    )


def build_weekly_summary_msg(
    week_label: str,
    total_hours: float,
    resource_pct: str,
    special_leave_days: int,
    daily_hours: dict[str, Optional[float]],
) -> str:
    day_names = {"월": None, "화": None, "수": None, "목": None, "금": None}
    for day_name, h in daily_hours.items():
        day_names[day_name] = h

    daily_line = " / ".join(
        f"{k}{v if v is not None else '-'}h" for k, v in daily_hours.items()
    )

    return (
        f"📊 지난주 리소스 리포트 ({week_label})\n\n"
        f"⏱ 총 업무시간: {total_hours}시간\n"
        f"📈 리소스: {resource_pct}\n"
        f"🎁 특별휴가: {special_leave_days}일 발생\n\n"
        f"일별: {daily_line}"
    )


def send_dm(client: WebClient, user_id: str, text: str) -> None:
    resp = client.conversations_open(users=user_id)
    channel_id = resp["channel"]["id"]
    client.chat_postMessage(channel=channel_id, text=text)
