# 마6 리소스 자동 측정봇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 슬랙 #mkt_마케팅6팀의 출퇴근 워크플로우 스레드를 매일 파싱해 업무시간·리소스%·특별휴가를 자동 계산하고 구글 시트에 기록 + 슬랙 DM 발송

**Architecture:** GitHub Actions cron(매일 08:00 KST, 매주 월 09:00 KST)이 Python 스크립트를 실행한다. 스크립트는 Slack API로 전일 스레드 리플을 수집 → 업무시간·리소스 계산 → 구글 시트 기록 → 특별휴가 해당자 DM 발송 순서로 동작한다.

**Tech Stack:** Python 3.11, slack_sdk, gspread, google-auth, pytest, GitHub Actions

---

## 파일 구조

```
slack-resource-bot/
├── main.py                  # CLI 진입점 (--mode daily|weekly)
├── slack_parser.py          # 슬랙 스레드 파싱 & 사용자 데이터 추출
├── calculator.py            # 업무시간·리소스%·특별휴가 계산
├── sheets.py                # 구글 시트 읽기/쓰기
├── notifier.py              # 슬랙 DM 발송
├── requirements.txt
├── tests/
│   ├── test_slack_parser.py
│   ├── test_calculator.py
│   └── test_notifier.py
└── .github/workflows/
    ├── daily.yml            # cron: '0 23 * * *' (KST 08:00)
    └── weekly.yml           # cron: '0 0 * * 1' (KST 월 09:00)
```

---

## Task 1: 프로젝트 초기화

**Files:**
- Create: `slack-resource-bot/requirements.txt`
- Create: `slack-resource-bot/tests/__init__.py`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p slack-resource-bot/tests
mkdir -p slack-resource-bot/.github/workflows
cd slack-resource-bot
```

- [ ] **Step 2: requirements.txt 작성**

```
slack-sdk==3.27.2
gspread==6.1.2
google-auth==2.29.0
pytest==8.2.0
python-dateutil==2.9.0
```

- [ ] **Step 3: 패키지 설치 확인**

```bash
pip install -r requirements.txt
```

Expected: 에러 없이 설치 완료

- [ ] **Step 4: tests/__init__.py 생성 (빈 파일)**

```bash
touch tests/__init__.py
```

- [ ] **Step 5: 커밋**

```bash
git add requirements.txt tests/__init__.py
git commit -m "chore: init slack-resource-bot project"
```

---

## Task 2: calculator.py — 업무시간·리소스·특별휴가 계산

**Files:**
- Create: `slack-resource-bot/calculator.py`
- Create: `slack-resource-bot/tests/test_calculator.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_calculator.py`:
```python
from datetime import datetime
from calculator import (
    calc_work_hours,
    calc_resource_pct,
    check_special_leave,
)

KST_FMT = "%H:%M"

def t(hhmm: str) -> datetime:
    return datetime.strptime(hhmm, KST_FMT)

# ── 업무시간 계산 ──────────────────────────────
def test_work_hours_basic():
    # 09:00 출근, 18:00 퇴근, 점심 1h 고정 공제 → 8h
    assert calc_work_hours(t("09:00"), t("18:00")) == 8.0

def test_work_hours_midnight():
    # 새벽 퇴근 (퇴근이 출근보다 앞선 경우 → 다음날로 처리)
    checkin  = datetime(2026, 6, 25, 9, 0)
    checkout = datetime(2026, 6, 26, 2, 30)
    assert calc_work_hours(checkin, checkout) == 16.5

def test_work_hours_negative_returns_zero():
    # 퇴근 없으면 None 반환
    assert calc_work_hours(t("09:00"), None) is None

# ── 리소스% ──────────────────────────────────
def test_resource_pct_under_32():
    assert calc_resource_pct(30.0) == "80%+"

def test_resource_pct_32_to_36():
    assert calc_resource_pct(34.0) == "80%+"

def test_resource_pct_36_to_40():
    assert calc_resource_pct(38.0) == "90%+"

def test_resource_pct_40_to_44():
    assert calc_resource_pct(42.0) == "100%+"

def test_resource_pct_44_to_48():
    assert calc_resource_pct(46.0) == "110%+"

def test_resource_pct_48_to_52():
    assert calc_resource_pct(50.0) == "120%+"

def test_resource_pct_52_plus():
    assert calc_resource_pct(54.0) == "130%+"

# ── 특별휴가 ─────────────────────────────────
def test_special_leave_case1_pass():
    result = check_special_leave(
        location="사무실",
        work_hours=15.5,
        is_jeonya=False,
        lunch_time=t("12:30"),   # 복귀 13:30 < 14:00 → OK
    )
    assert result == "CASE1"

def test_special_leave_case1_fail_lunch():
    # 점심 13:10 → 복귀 14:10 > 14:00 → 특휴 없음
    result = check_special_leave(
        location="사무실",
        work_hours=15.5,
        is_jeonya=False,
        lunch_time=t("13:10"),
    )
    assert result is None

def test_special_leave_case1_fail_hours():
    result = check_special_leave(
        location="사무실",
        work_hours=14.9,
        is_jeonya=False,
        lunch_time=t("12:00"),
    )
    assert result is None

def test_special_leave_case2_pass():
    result = check_special_leave(
        location="사무실",
        work_hours=11.0,
        is_jeonya=True,
        lunch_time=t("12:00"),
    )
    assert result == "CASE2"

def test_special_leave_case2_fail_hours():
    result = check_special_leave(
        location="사무실",
        work_hours=10.9,
        is_jeonya=True,
        lunch_time=t("12:00"),
    )
    assert result is None

def test_special_leave_no_lunch_time():
    # 점심 리플 없으면 14시 룰 통과로 처리
    result = check_special_leave(
        location="사무실",
        work_hours=15.5,
        is_jeonya=False,
        lunch_time=None,
    )
    assert result == "CASE1"

def test_special_leave_jaetaek_excluded():
    # 재택은 특별휴가 없음
    result = check_special_leave(
        location="재택",
        work_hours=20.0,
        is_jeonya=False,
        lunch_time=None,
    )
    assert result is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_calculator.py -v
```

Expected: `ModuleNotFoundError: No module named 'calculator'`

- [ ] **Step 3: calculator.py 구현**

```python
from datetime import datetime, timedelta
from typing import Optional

LUNCH_HOURS = 1.0  # 점심 고정 공제

def calc_work_hours(
    checkin: Optional[datetime],
    checkout: Optional[datetime],
) -> Optional[float]:
    """업무시간 = 퇴근 - 출근 - 1h(점심). 둘 중 하나 없으면 None."""
    if checkin is None or checkout is None:
        return None
    # 새벽 퇴근: checkout < checkin이면 다음날로 처리
    if checkout < checkin:
        checkout += timedelta(days=1)
    diff = (checkout - checkin).total_seconds() / 3600
    return round(diff - LUNCH_HOURS, 2)


def calc_resource_pct(weekly_hours: float) -> str:
    """주간 업무시간 → 리소스% 문자열 반환."""
    if weekly_hours < 36:
        return "80%+"
    elif weekly_hours < 40:
        return "90%+"
    elif weekly_hours < 44:
        return "100%+"
    elif weekly_hours < 48:
        return "110%+"
    elif weekly_hours < 52:
        return "120%+"
    else:
        return "130%+"


def _lunch_before_14(lunch_time: Optional[datetime]) -> bool:
    """점심 리플 + 1h ≤ 14:00 여부. lunch_time=None이면 True(통과)."""
    if lunch_time is None:
        return True
    return_time = lunch_time + timedelta(hours=1)
    return return_time.hour < 14 or (return_time.hour == 14 and return_time.minute == 0)


def check_special_leave(
    location: str,
    work_hours: Optional[float],
    is_jeonya: bool,
    lunch_time: Optional[datetime],
) -> Optional[str]:
    """특별휴가 판정. 'CASE1' | 'CASE2' | None 반환."""
    if work_hours is None:
        return None
    is_office = location in ("사무실", "전야재", "미분류")
    lunch_ok = _lunch_before_14(lunch_time)

    # CASE2: 전야재 우선 체크
    if is_jeonya and is_office and lunch_ok and work_hours >= 11.0:
        return "CASE2"
    # CASE1: 평일 15h+
    if is_office and lunch_ok and work_hours >= 15.0:
        return "CASE1"
    return None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_calculator.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add calculator.py tests/test_calculator.py
git commit -m "feat: add work hours, resource%, special leave calculator"
```

---

## Task 3: slack_parser.py — 슬랙 스레드 파싱

**Files:**
- Create: `slack-resource-bot/slack_parser.py`
- Create: `slack-resource-bot/tests/test_slack_parser.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_slack_parser.py`:
```python
from slack_parser import parse_location, find_workflow_threads, extract_user_records

def test_parse_location_office():
    assert parse_location("사무실 출근했습니다") == "사무실"

def test_parse_location_jaetaek():
    assert parse_location("업무 시작하겠습니다 (재택)") == "재택"

def test_parse_location_jeonya():
    assert parse_location("출근입니다/전야재") == "전야재"

def test_parse_location_ojeon_jaetaek():
    assert parse_location("업무 시작하겠습니다 (오전재택)") == "재택"

def test_parse_location_no_keyword():
    assert parse_location("5분전 출근했습니다") == "미분류"

def test_find_workflow_threads_checkin():
    """출근 기록 워크플로우 스레드 ts 찾기."""
    messages = [
        {"text": "오늘도 파이팅 해보아요!", "ts": "1750000000.000100", "subtype": "bot_message", "username": "출근 기록"},
        {"text": "뭔가 다른 메시지", "ts": "1750000001.000100"},
    ]
    result = find_workflow_threads(messages)
    assert result["checkin_ts"] == "1750000000.000100"

def test_extract_user_records():
    """스레드 리플에서 유저별 첫 번째 리플 타임스탬프 추출."""
    replies = [
        {"user": "U001", "ts": "1750000100.000100", "text": "사무실 출근했습니다"},
        {"user": "U001", "ts": "1750000200.000100", "text": "잠깐요"},  # 두 번째 리플 → 무시
        {"user": "U002", "ts": "1750000150.000100", "text": "재택 시작"},
    ]
    result = extract_user_records(replies)
    assert result["U001"]["ts"] == "1750000100.000100"
    assert result["U001"]["text"] == "사무실 출근했습니다"
    assert result["U002"]["ts"] == "1750000150.000100"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_slack_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'slack_parser'`

- [ ] **Step 3: slack_parser.py 구현**

```python
from datetime import datetime, timezone, timedelta
from typing import Optional
from slack_sdk import WebClient

KST = timezone(timedelta(hours=9))

LOCATION_KEYWORDS = {
    "전야재": "전야재",
    "오전재택": "재택",
    "재택": "재택",
    "사무실": "사무실",
}

WORKFLOW_KEYWORDS = {
    "checkin":  ["출근 기록", "출근기록"],
    "lunch":    ["점심 기록", "점심기록"],
    "checkout": ["퇴근 기록", "퇴근기록"],
}


def parse_location(text: str) -> str:
    """출근 메시지에서 위치 키워드 추출. 없으면 '미분류'."""
    for keyword, location in LOCATION_KEYWORDS.items():
        if keyword in text:
            return location
    return "미분류"


def find_workflow_threads(messages: list[dict]) -> dict[str, Optional[str]]:
    """채널 메시지 목록에서 출근/점심/퇴근 워크플로우 스레드 ts 반환."""
    result = {"checkin_ts": None, "lunch_ts": None, "checkout_ts": None}
    for msg in messages:
        username = msg.get("username", "") or msg.get("bot_profile", {}).get("name", "")
        for key, keywords in WORKFLOW_KEYWORDS.items():
            for kw in keywords:
                if kw in username or kw in msg.get("text", ""):
                    result[f"{key}_ts"] = msg["ts"]
    return result


def extract_user_records(replies: list[dict]) -> dict[str, dict]:
    """리플 목록에서 유저별 첫 번째 리플만 추출. {user_id: {ts, text}}"""
    seen: dict[str, dict] = {}
    for reply in replies:
        uid = reply.get("user")
        if uid and uid not in seen:
            seen[uid] = {"ts": reply["ts"], "text": reply.get("text", "")}
    return seen


def ts_to_kst(ts: str) -> datetime:
    """Slack timestamp(문자열) → KST datetime."""
    return datetime.fromtimestamp(float(ts), tz=KST)


def fetch_day_records(client: WebClient, channel_id: str, target_date: datetime) -> list[dict]:
    """
    target_date(KST) 하루치 출근/점심/퇴근 스레드를 파싱해
    유저별 레코드 리스트 반환.
    반환 형태: [{user_id, checkin_dt, lunch_dt, checkout_dt, location, is_jeonya}, ...]
    """
    # 하루 범위 (KST 00:00 ~ 익일 07:59) → UTC epoch
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = target_date.replace(hour=23, minute=59, second=59)

    oldest = str(day_start.timestamp())
    latest = str(day_end.timestamp())

    resp = client.conversations_history(
        channel=channel_id, oldest=oldest, latest=latest, limit=200
    )
    messages = resp["messages"]

    threads = find_workflow_threads(messages)

    def get_replies(ts: Optional[str]) -> dict[str, dict]:
        if not ts:
            return {}
        r = client.conversations_replies(channel=channel_id, ts=ts, limit=200)
        return extract_user_records(r["messages"][1:])  # 첫 메시지는 봇 원문 제외

    checkin_map  = get_replies(threads["checkin_ts"])
    lunch_map    = get_replies(threads["lunch_ts"])
    checkout_map = get_replies(threads["checkout_ts"])

    all_users = set(checkin_map) | set(checkout_map)
    records = []
    for uid in all_users:
        ci = checkin_map.get(uid)
        lu = lunch_map.get(uid)
        co = checkout_map.get(uid)

        checkin_dt  = ts_to_kst(ci["ts"]) if ci else None
        lunch_dt    = ts_to_kst(lu["ts"]) if lu else None
        checkout_dt = ts_to_kst(co["ts"]) if co else None

        location  = parse_location(ci["text"]) if ci else "미분류"
        is_jeonya = "전야재" in (ci["text"] if ci else "")

        records.append({
            "user_id":     uid,
            "checkin_dt":  checkin_dt,
            "lunch_dt":    lunch_dt,
            "checkout_dt": checkout_dt,
            "location":    location,
            "is_jeonya":   is_jeonya,
        })
    return records
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_slack_parser.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add slack_parser.py tests/test_slack_parser.py
git commit -m "feat: add slack thread parser"
```

---

## Task 4: sheets.py — 구글 시트 기록

**Files:**
- Create: `slack-resource-bot/sheets.py`

- [ ] **Step 1: sheets.py 구현**

```python
import json
import os
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = ["날짜", "슬랙ID", "출근시간", "점심시간", "퇴근시간", "위치", "전야재", "업무시간", "리소스", "특휴여부"]


def get_sheet(sheet_id: str) -> gspread.Worksheet:
    """환경변수에서 서비스 계정 JSON 읽어 시트 반환."""
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet("리소스기록")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="리소스기록", rows=1000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    return ws


def fmt_time(dt: Optional[datetime]) -> str:
    return dt.strftime("%H:%M") if dt else "-"


def append_daily_record(
    ws: gspread.Worksheet,
    date: datetime,
    user_id: str,
    checkin_dt: Optional[datetime],
    lunch_dt: Optional[datetime],
    checkout_dt: Optional[datetime],
    location: str,
    is_jeonya: bool,
    work_hours: Optional[float],
    resource_pct: Optional[str],
    special_leave: Optional[str],
) -> None:
    """일별 레코드 1행 추가."""
    row = [
        date.strftime("%Y-%m-%d"),
        user_id,
        fmt_time(checkin_dt),
        fmt_time(lunch_dt),
        fmt_time(checkout_dt),
        location,
        "Y" if is_jeonya else "N",
        str(work_hours) if work_hours is not None else "-",
        resource_pct or "-",
        special_leave or "-",
    ]
    ws.append_row(row)


def read_week_records(ws: gspread.Worksheet, week_start: datetime, week_end: datetime) -> list[dict]:
    """week_start ~ week_end 기간 레코드 반환."""
    all_rows = ws.get_all_records()
    result = []
    for row in all_rows:
        try:
            row_date = datetime.strptime(row["날짜"], "%Y-%m-%d")
        except (ValueError, KeyError):
            continue
        if week_start <= row_date <= week_end:
            result.append(row)
    return result
```

- [ ] **Step 2: 커밋**

```bash
git add sheets.py
git commit -m "feat: add google sheets writer"
```

---

## Task 5: notifier.py — 슬랙 DM 발송

**Files:**
- Create: `slack-resource-bot/notifier.py`
- Create: `slack-resource-bot/tests/test_notifier.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_notifier.py`:
```python
from notifier import build_special_leave_msg, build_weekly_summary_msg

def test_build_special_leave_case1():
    msg = build_special_leave_msg(
        date_str="6/25",
        location="사무실",
        work_hours=15.5,
        case="CASE1",
    )
    assert "특별휴가" in msg
    assert "15.5시간" in msg
    assert "CASE1" in msg

def test_build_special_leave_case2():
    msg = build_special_leave_msg(
        date_str="6/25",
        location="전야재",
        work_hours=11.0,
        case="CASE2",
    )
    assert "전야재" in msg
    assert "CASE2" in msg

def test_build_weekly_summary():
    daily = {
        "월": 9.0, "화": 8.0, "수": 9.5, "목": 8.0, "금": 8.0
    }
    msg = build_weekly_summary_msg(
        week_label="6/16~6/20",
        total_hours=42.5,
        resource_pct="100%+",
        special_leave_days=0,
        daily_hours=daily,
    )
    assert "42.5시간" in msg
    assert "100%+" in msg
    assert "6/16~6/20" in msg
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_notifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'notifier'`

- [ ] **Step 3: notifier.py 구현**

```python
import os
from typing import Optional
from slack_sdk import WebClient


def build_special_leave_msg(
    date_str: str,
    location: str,
    work_hours: float,
    case: str,
) -> str:
    case_desc = {
        "CASE1": "평일 사무실 15시간 이상 근무",
        "CASE2": "전야재 후 11시간 이상 근무",
    }.get(case, case)
    return (
        f"🎁 어제({date_str}) 특별휴가가 발생했어요!\n"
        f"📍 위치: {location}  |  ⏱ 업무시간: {work_hours}시간\n"
        f"✅ {case} 조건 충족 ({case_desc})\n"
        f"특별휴가 신청은 HR에 문의해주세요."
    )


def build_weekly_summary_msg(
    week_label: str,
    total_hours: float,
    resource_pct: str,
    special_leave_days: int,
    daily_hours: dict[str, Optional[float]],
) -> str:
    day_parts = " / ".join(
        f"{day}{f'{h}h' if h else '-'}"
        for day, h in daily_hours.items()
    )
    return (
        f"📊 지난주 리소스 리포트 ({week_label})\n\n"
        f"⏱ 총 업무시간: {total_hours}시간\n"
        f"📈 리소스: {resource_pct}\n"
        f"🎁 특별휴가: {special_leave_days}일 발생\n\n"
        f"일별: {day_parts}"
    )


def send_dm(client: WebClient, user_id: str, text: str) -> None:
    """유저에게 DM 발송."""
    resp = client.conversations_open(users=user_id)
    channel_id = resp["channel"]["id"]
    client.chat_postMessage(channel=channel_id, text=text)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_notifier.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add notifier.py tests/test_notifier.py
git commit -m "feat: add slack DM notifier"
```

---

## Task 6: main.py — 메인 실행 진입점

**Files:**
- Create: `slack-resource-bot/main.py`

- [ ] **Step 1: main.py 구현**

```python
import os
import sys
from datetime import datetime, timezone, timedelta

from slack_sdk import WebClient

from slack_parser import fetch_day_records
from calculator import calc_work_hours, calc_resource_pct, check_special_leave
from sheets import get_sheet, append_daily_record, read_week_records
from notifier import build_special_leave_msg, build_weekly_summary_msg, send_dm

KST = timezone(timedelta(hours=9))
DAY_KR = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


def run_daily() -> None:
    """매일 08:00 KST: 전일 데이터 처리."""
    client     = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    sheet_id   = os.environ["GOOGLE_SHEET_ID"]

    today     = datetime.now(tz=KST)
    yesterday = today - timedelta(days=1)

    ws = get_sheet(sheet_id)
    records = fetch_day_records(client, channel_id, yesterday)

    for rec in records:
        work_hours = calc_work_hours(rec["checkin_dt"], rec["checkout_dt"])
        resource_pct = calc_resource_pct(work_hours) if work_hours else None
        special_leave = check_special_leave(
            location=rec["location"],
            work_hours=work_hours,
            is_jeonya=rec["is_jeonya"],
            lunch_time=rec["lunch_dt"],
        )

        append_daily_record(
            ws=ws,
            date=yesterday,
            user_id=rec["user_id"],
            checkin_dt=rec["checkin_dt"],
            lunch_dt=rec["lunch_dt"],
            checkout_dt=rec["checkout_dt"],
            location=rec["location"],
            is_jeonya=rec["is_jeonya"],
            work_hours=work_hours,
            resource_pct=resource_pct,
            special_leave=special_leave,
        )

        if special_leave:
            msg = build_special_leave_msg(
                date_str=yesterday.strftime("%-m/%-d"),
                location=rec["location"],
                work_hours=round(work_hours, 1),
                case=special_leave,
            )
            send_dm(client, rec["user_id"], msg)
            print(f"[특휴DM] {rec['user_id']} → {special_leave}")

    print(f"[daily] {yesterday.strftime('%Y-%m-%d')} 처리 완료: {len(records)}명")


def run_weekly() -> None:
    """매주 월요일 09:00 KST: 지난주 주간 요약 DM."""
    client     = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    sheet_id   = os.environ["GOOGLE_SHEET_ID"]

    today      = datetime.now(tz=KST)
    # 지난주 월~금
    week_start = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0)
    week_end   = week_start + timedelta(days=4, hours=23, minutes=59)

    ws = get_sheet(sheet_id)
    rows = read_week_records(ws, week_start, week_end)

    # 유저별 집계
    user_data: dict[str, dict] = {}
    for row in rows:
        uid = row["슬랙ID"]
        if uid not in user_data:
            user_data[uid] = {"hours": [], "special_leave_days": 0, "daily": {}}
        try:
            h = float(row["업무시간"])
            user_data[uid]["hours"].append(h)
            dow = datetime.strptime(row["날짜"], "%Y-%m-%d").weekday()
            user_data[uid]["daily"][DAY_KR[dow]] = h
        except (ValueError, KeyError):
            pass
        if row.get("특휴여부") not in ("-", "", None):
            user_data[uid]["special_leave_days"] += 1

    week_label = f"{week_start.strftime('%-m/%-d')}~{week_end.strftime('%-m/%-d')}"

    for uid, data in user_data.items():
        total = round(sum(data["hours"]), 1)
        resource_pct = calc_resource_pct(total)
        daily_hours = {d: data["daily"].get(d) for d in ["월", "화", "수", "목", "금"]}
        msg = build_weekly_summary_msg(
            week_label=week_label,
            total_hours=total,
            resource_pct=resource_pct,
            special_leave_days=data["special_leave_days"],
            daily_hours=daily_hours,
        )
        send_dm(client, uid, msg)
        print(f"[weekly DM] {uid} → {total}h / {resource_pct}")

    print(f"[weekly] {week_label} 요약 DM 발송 완료: {len(user_data)}명")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if mode == "daily":
        run_daily()
    elif mode == "weekly":
        run_weekly()
    else:
        print(f"Unknown mode: {mode}. Use 'daily' or 'weekly'.")
        sys.exit(1)
```

- [ ] **Step 2: 로컬 dry-run 확인 (환경변수 없이 import만 테스트)**

```bash
python -c "import main; print('import OK')"
```

Expected: `import OK`

- [ ] **Step 3: 커밋**

```bash
git add main.py
git commit -m "feat: add main entry point (daily/weekly mode)"
```

---

## Task 7: GitHub Actions 워크플로우

**Files:**
- Create: `slack-resource-bot/.github/workflows/daily.yml`
- Create: `slack-resource-bot/.github/workflows/weekly.yml`

- [ ] **Step 1: daily.yml 작성**

```yaml
name: Daily Resource Bot

on:
  schedule:
    - cron: '0 23 * * *'   # 매일 23:00 UTC = 08:00 KST
  workflow_dispatch:         # 수동 실행 가능

jobs:
  run:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: slack-resource-bot
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py daily
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.SLACK_CHANNEL_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
```

- [ ] **Step 2: weekly.yml 작성**

```yaml
name: Weekly Resource Summary

on:
  schedule:
    - cron: '0 0 * * 1'    # 매주 월요일 00:00 UTC = 09:00 KST
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: slack-resource-bot
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py weekly
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.SLACK_CHANNEL_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
```

- [ ] **Step 3: 전체 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 최종 커밋 & 푸시**

```bash
git add .github/workflows/daily.yml .github/workflows/weekly.yml
git commit -m "feat: add GitHub Actions cron workflows"
git push
```

---

## Task 8: GitHub Secrets 등록 및 실제 연동

- [ ] **Step 1: Slack Bot 앱 생성**

1. https://api.slack.com/apps → "Create New App" → "From scratch"
2. App Name: `마6 리소스봇`, Workspace: MADUP
3. OAuth & Permissions → Bot Token Scopes 추가:
   - `channels:history`
   - `groups:history`
   - `users:read`
   - `chat:write`
   - `im:write`
4. "Install to Workspace" → Bot User OAuth Token (`xoxb-...`) 복사

- [ ] **Step 2: Google Service Account 생성**

1. Google Cloud Console → IAM → 서비스 계정 생성
2. 키 생성 → JSON 다운로드
3. 대상 구글 시트 → 공유 → 서비스 계정 이메일 추가 (편집자)

- [ ] **Step 3: GitHub Secrets 등록**

GitHub 레포 → Settings → Secrets → Actions에 4개 등록:
```
SLACK_BOT_TOKEN           = xoxb-...
SLACK_CHANNEL_ID          = C0XXXXXXXX  (채널 ID, 우클릭→채널 세부정보)
GOOGLE_SERVICE_ACCOUNT_JSON = { ... JSON 전체 ... }
GOOGLE_SHEET_ID           = 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

- [ ] **Step 4: workflow_dispatch로 수동 테스트**

GitHub Actions → Daily Resource Bot → "Run workflow" 클릭 → 로그 확인

Expected: 구글 시트에 행 추가, 특별휴가 해당자 있으면 DM 수신

---

## Task 9: 매주 금요일 — 주간 리소스% 시트 F열 자동 기입

**Files:**
- Modify: `slack-resource-bot/sheets.py`
- Modify: `slack-resource-bot/main.py`
- Create: `slack-resource-bot/.github/workflows/friday.yml`

**대상 시트:** `1SZWV7msK_C7ZUs-OrxVw6CRqgeHFCMvWt3eFCz-76cU` (gid=184935827)
**매핑 방식:** 슬랙 display_name ↔ 시트 B열 이름 (공백·성씨 정규화 후 매칭)

- [ ] **Step 1: sheets.py에 F열 기입 함수 추가**

```python
def write_resource_pct_to_weekly_sheet(
    resource_sheet_id: str,
    name_to_pct: dict[str, str],  # {"김성규": "100%+", ...}
) -> None:
    """주간 리소스 시트 F열에 리소스% 기입. B열 이름으로 행 매칭."""
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(resource_sheet_id)
    # gid=184935827 탭
    ws = sh.get_worksheet_by_id(184935827)

    all_values = ws.get_all_values()
    updates = []
    for i, row in enumerate(all_values):
        if len(row) < 2:
            continue
        cell_name = row[1].strip()  # B열 이름
        for slack_name, pct in name_to_pct.items():
            if _name_match(cell_name, slack_name):
                # F열 = index 5 (0-based), gspread row = i+1 (1-based)
                updates.append({"range": f"F{i+1}", "values": [[pct]]})
                break
    if updates:
        ws.batch_update(updates)


def _name_match(sheet_name: str, slack_name: str) -> bool:
    """성씨+이름 공백 제거 후 포함 여부로 매칭."""
    s = sheet_name.replace(" ", "")
    n = slack_name.replace(" ", "")
    return s == n or s in n or n in s
```

- [ ] **Step 2: slack_parser.py에 display_name 조회 함수 추가**

```python
def get_display_name(client: WebClient, user_id: str) -> str:
    """슬랙 user_id → display_name (또는 real_name) 반환."""
    resp = client.users_info(user=user_id)
    profile = resp["user"]["profile"]
    return profile.get("display_name") or profile.get("real_name", "")
```

- [ ] **Step 3: main.py에 run_friday() 추가**

```python
def run_friday() -> None:
    """매주 금요일 18:00 KST: 이번 주(월~금) 리소스% → 시트 F열 기입."""
    client              = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    sheet_id            = os.environ["GOOGLE_SHEET_ID"]         # 일별 기록 시트
    resource_sheet_id   = os.environ["RESOURCE_SHEET_ID"]       # 주간 리소스 시트

    today      = datetime.now(tz=KST)
    week_start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0)
    week_end   = today.replace(hour=23, minute=59, second=59)

    ws = get_sheet(sheet_id)
    rows = read_week_records(ws, week_start, week_end)

    # 유저별 총 업무시간 집계
    user_hours: dict[str, float] = {}
    for row in rows:
        uid = row["슬랙ID"]
        try:
            h = float(row["업무시간"])
            user_hours[uid] = user_hours.get(uid, 0.0) + h
        except (ValueError, KeyError):
            pass

    # 슬랙 display_name → 리소스% 매핑
    from slack_parser import get_display_name
    name_to_pct: dict[str, str] = {}
    for uid, total_hours in user_hours.items():
        display_name = get_display_name(client, uid)
        if display_name:
            name_to_pct[display_name] = calc_resource_pct(round(total_hours, 1))
            print(f"[friday] {display_name}: {total_hours:.1f}h → {name_to_pct[display_name]}")

    from sheets import write_resource_pct_to_weekly_sheet
    write_resource_pct_to_weekly_sheet(resource_sheet_id, name_to_pct)
    print(f"[friday] F열 기입 완료: {len(name_to_pct)}명")
```

main.py `__main__` 블록에 분기 추가:
```python
    elif mode == "friday":
        run_friday()
```

- [ ] **Step 4: friday.yml 작성**

```yaml
name: Friday Resource Sheet Update

on:
  schedule:
    - cron: '0 9 * * 5'   # 매주 금요일 09:00 UTC = 18:00 KST
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: slack-resource-bot
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py friday
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.SLACK_CHANNEL_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          RESOURCE_SHEET_ID: ${{ secrets.RESOURCE_SHEET_ID }}
```

- [ ] **Step 5: GitHub Secret 추가**

```
RESOURCE_SHEET_ID = 1SZWV7msK_C7ZUs-OrxVw6CRqgeHFCMvWt3eFCz-76cU
```

- [ ] **Step 6: workflow_dispatch로 수동 테스트**

GitHub Actions → Friday Resource Sheet Update → "Run workflow" → 시트 F열 확인

Expected: 이번 주 출퇴근 기록 있는 팀원 이름 행의 F열에 리소스% 값 기입됨

- [ ] **Step 7: 커밋**

```bash
git add sheets.py slack_parser.py main.py .github/workflows/friday.yml
git commit -m "feat: add friday weekly resource% sheet writer"
git push
```

---

## 완료 기준

- [ ] `pytest tests/ -v` 전체 통과
- [ ] GitHub Actions 수동 실행 성공
- [ ] 구글 시트 리소스기록 탭에 당일 레코드 기록됨
- [ ] 특별휴가 해당자에게 DM 수신 확인
- [ ] 주간 요약 DM 수신 확인 (월요일)
- [ ] 매주 금요일 주간 리소스 시트 F열에 리소스% 자동 기입됨
