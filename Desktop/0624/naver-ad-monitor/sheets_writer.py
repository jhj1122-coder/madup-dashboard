# sheets_writer.py
import json
import os
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID, RAW_SHEET_NAME, SUMMARY_SHEET_NAME, TARGET_BRAND

KST = timezone(timedelta(hours=9))
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

RAW_HEADERS = [
    "수집시간", "키워드", "환경", "순위", "광고주",
    "제목", "설명", "표시URL", "이미지",
]


def _get_client() -> gspread.Client:
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, name: str, headers: list) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=5000, cols=len(headers))
        ws.append_row(headers)
    return ws


def build_raw_row(
    collected_at: str, keyword: str, env: str, rank: int,
    advertiser: str, headline: str, description: str,
    display_url: str, image_url: str,
) -> list:
    image_formula = f'=IMAGE("{image_url}")' if image_url else ""
    return [
        collected_at, keyword, env, rank, advertiser,
        headline, description, display_url, image_formula,
    ]


def append_raw_rows(rows: list[list]) -> None:
    gc = _get_client()
    ss = gc.open_by_key(SHEET_ID)
    ws = _get_or_create_sheet(ss, RAW_SHEET_NAME, RAW_HEADERS)
    ws.append_rows(rows, value_input_option="USER_ENTERED")


def refresh_summary(all_rows: list[list]) -> None:
    """SUMMARY 탭을 최신 수집 결과로 전체 갱신 + 삼성화재 행 강조"""
    gc = _get_client()
    ss = gc.open_by_key(SHEET_ID)
    ws = _get_or_create_sheet(ss, SUMMARY_SHEET_NAME, RAW_HEADERS)

    ws.clear()
    ws.append_row(RAW_HEADERS)
    if all_rows:
        ws.append_rows(all_rows, value_input_option="USER_ENTERED")

    all_values = ws.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) > 4 and TARGET_BRAND in row[4]:
            ws.format(
                f"A{i}:I{i}",
                {"backgroundColor": {"red": 1.0, "green": 0.898, "blue": 0.6}},
            )
