import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials

KST = timezone(timedelta(hours=9))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SHEET_HEADERS = ["날짜", "이름", "출근시간", "점심시간", "퇴근시간", "위치", "업무시간", "특휴여부"]
LOG_SHEET_NAME = "리소스기록"


def _get_client() -> gspread.Client:
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_log_sheet(sheet_id: str) -> gspread.Worksheet:
    gc = _get_client()
    spreadsheet = gc.open_by_key(sheet_id)
    try:
        ws = spreadsheet.worksheet(LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=LOG_SHEET_NAME, rows=1000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    return ws


def _fmt_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%H:%M")


def append_daily_record(
    ws: gspread.Worksheet,
    date_str: str,
    display_name: str,
    checkin_ts: Optional[datetime],
    lunch_ts: Optional[datetime],
    checkout_ts: Optional[datetime],
    location: str,
    work_hours: Optional[float],
    special_leave: Optional[str],
) -> None:
    row = [
        date_str,
        display_name,
        _fmt_time(checkin_ts),
        _fmt_time(lunch_ts),
        _fmt_time(checkout_ts),
        location,
        str(work_hours) if work_hours is not None else "-",
        special_leave or "-",
    ]
    ws.append_row(row)


def read_week_records(ws: gspread.Worksheet, week_start: datetime, week_end: datetime) -> list[dict]:
    all_rows = ws.get_all_records()
    results = []
    for row in all_rows:
        try:
            row_date = datetime.strptime(row["날짜"], "%Y-%m-%d").replace(tzinfo=KST)
        except (ValueError, KeyError):
            continue
        if week_start <= row_date <= week_end:
            results.append(row)
    return results


def _name_match(sheet_name: str, slack_name: str) -> bool:
    a = sheet_name.replace(" ", "").strip()
    b = slack_name.replace(" ", "").strip()
    return a in b or b in a


def write_resource_pct_to_weekly_sheet(
    resource_sheet_id: str,
    name_to_pct: dict[str, str],
    gid: int = 184935827,
) -> None:
    gc = _get_client()
    spreadsheet = gc.open_by_key(resource_sheet_id)

    # gid로 워크시트 찾기
    ws = None
    for sheet in spreadsheet.worksheets():
        if sheet.id == gid:
            ws = sheet
            break
    if ws is None:
        raise ValueError(f"gid={gid} 시트를 찾을 수 없습니다")

    all_rows = ws.get_all_values()
    # B열(index 1)이 이름, F열(index 5)에 리소스% 기록
    for i, row in enumerate(all_rows[1:], start=2):  # 헤더 제외, 1-indexed
        if len(row) < 2:
            continue
        sheet_name = row[1]
        for slack_name, pct in name_to_pct.items():
            if _name_match(sheet_name, slack_name):
                ws.update_cell(i, 6, pct)  # F열 = 6번째 열
                break
