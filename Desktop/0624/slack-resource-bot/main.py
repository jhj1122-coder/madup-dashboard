import os
import sys
from datetime import datetime, timezone, timedelta

from slack_sdk import WebClient

from calculator import calc_work_hours, calc_resource_pct, check_special_leave
from slack_parser import fetch_day_records
from sheets import get_log_sheet, append_daily_record, read_week_records, write_resource_pct_to_weekly_sheet
from notifier import build_special_leave_msg, build_weekly_summary_msg, send_dm

KST = timezone(timedelta(hours=9))

RESOURCE_SHEET_ID = "1SZWV7msK_C7ZUs-OrxVw6CRqgeHFCMvWt3eFCz-76cU"
RESOURCE_SHEET_GID = 184935827


def _get_client() -> WebClient:
    return WebClient(token=os.environ["SLACK_BOT_TOKEN"])


def run_daily() -> None:
    client = _get_client()
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    yesterday = datetime.now(tz=KST) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")

    print(f"[daily] 처리 날짜: {date_str}")

    records = fetch_day_records(client, channel_id, yesterday)
    ws = get_log_sheet(sheet_id)

    for rec in records:
        work_hours = calc_work_hours(rec["checkin_ts"], rec["checkout_ts"])
        special_leave = check_special_leave(
            rec["location"], work_hours or 0.0, rec["is_jeonya"], rec["lunch_ts"]
        ) if work_hours is not None else None

        append_daily_record(
            ws,
            date_str=date_str,
            display_name=rec["display_name"],
            checkin_ts=rec["checkin_ts"],
            lunch_ts=rec["lunch_ts"],
            checkout_ts=rec["checkout_ts"],
            location=rec["location"],
            work_hours=work_hours,
            special_leave=special_leave,
        )

        if special_leave:
            msg = build_special_leave_msg(
                date_str=f"{yesterday.month}/{yesterday.day}",
                location=rec["location"],
                work_hours=work_hours,
                case=special_leave,
            )
            send_dm(client, rec["user_id"], msg)
            print(f"  특휴 DM 발송: {rec['display_name']} ({special_leave})")

    print(f"[daily] 완료 — {len(records)}명 처리")


def run_friday() -> None:
    """지난주 리소스% 계산 → 주간 시트 F열 기록"""
    client = _get_client()
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    ws = get_log_sheet(sheet_id)

    today = datetime.now(tz=KST)
    # 오늘이 월요일(weekday=0) 기준 → 지난주 월~금
    week_start = today - timedelta(days=today.weekday() + 7)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=4, hours=23, minutes=59, seconds=59)

    week_label = f"{week_start.month}/{week_start.day}~{week_end.month}/{week_end.day}"
    print(f"[friday] 집계 주간: {week_label}")

    rows = read_week_records(ws, week_start, week_end)

    # 이름별 총 업무시간 합산
    name_hours: dict[str, float] = {}
    for row in rows:
        name = row.get("이름", "")
        try:
            h = float(row.get("업무시간", "0"))
        except ValueError:
            h = 0.0
        name_hours[name] = name_hours.get(name, 0.0) + h

    name_to_pct = {name: calc_resource_pct(hours) for name, hours in name_hours.items()}

    write_resource_pct_to_weekly_sheet(RESOURCE_SHEET_ID, name_to_pct, RESOURCE_SHEET_GID)
    print(f"[friday] F열 기록 완료 — {len(name_to_pct)}명")


def run_weekly() -> None:
    """전원에게 주간 요약 DM 발송"""
    client = _get_client()
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    ws = get_log_sheet(sheet_id)

    today = datetime.now(tz=KST)
    week_start = today - timedelta(days=today.weekday() + 7)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=4, hours=23, minutes=59, seconds=59)

    week_label = f"{week_start.month}/{week_start.day}~{week_end.month}/{week_end.day}"
    rows = read_week_records(ws, week_start, week_end)

    # 이름/user_id별로 그룹핑
    from collections import defaultdict
    user_rows: dict[str, list[dict]] = defaultdict(list)
    # 시트에는 user_id가 없으므로 이름 기준 집계, DM은 Slack에서 이름→user_id 매핑 필요
    # user_id를 시트에 별도 저장하지 않아 weekly DM은 채널 멤버 목록 기반으로 발송
    members_resp = client.conversations_members(channel=os.environ["SLACK_CHANNEL_ID"])
    member_ids = members_resp.get("members", [])

    # 이름→user_id 역매핑
    from slack_parser import get_display_name
    name_to_uid: dict[str, str] = {}
    for uid in member_ids:
        try:
            name = get_display_name(client, uid)
            name_to_uid[name] = uid
        except Exception:
            pass

    # 이름별 일별 업무시간
    day_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금"}
    name_daily: dict[str, dict[str, float]] = defaultdict(dict)
    name_special: dict[str, int] = defaultdict(int)

    for row in rows:
        name = row.get("이름", "")
        try:
            row_date = datetime.strptime(row["날짜"], "%Y-%m-%d").replace(tzinfo=KST)
            day_label = day_map.get(row_date.weekday(), "?")
        except (ValueError, KeyError):
            day_label = "?"
        try:
            h = float(row.get("업무시간", "0"))
        except ValueError:
            h = 0.0
        name_daily[name][day_label] = h
        if row.get("특휴여부") not in ("-", "", None):
            name_special[name] += 1

    for name, daily in name_daily.items():
        total = sum(daily.values())
        resource_pct = calc_resource_pct(total)
        special_days = name_special.get(name, 0)

        ordered_daily = {k: daily.get(k) for k in ["월", "화", "수", "목", "금"]}
        msg = build_weekly_summary_msg(week_label, total, resource_pct, special_days, ordered_daily)

        uid = name_to_uid.get(name)
        if uid:
            send_dm(client, uid, msg)
            print(f"  주간 DM 발송: {name}")
        else:
            print(f"  [SKIP] Slack 유저 매핑 실패: {name}")

    print(f"[weekly] 완료")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [daily|weekly|friday]")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "daily":
        run_daily()
    elif mode == "weekly":
        run_weekly()
    elif mode == "friday":
        run_friday()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
