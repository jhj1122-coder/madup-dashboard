# tests/test_sheets_writer.py
import pytest
from unittest.mock import MagicMock, patch
from sheets_writer import build_raw_row, RAW_HEADERS


def test_build_raw_row_returns_correct_length():
    row = build_raw_row(
        collected_at="2026-06-26 09:00",
        keyword="여행자보험",
        env="PC",
        rank=1,
        advertiser="삼성화재",
        headline="여행자보험 1위",
        description="해외여행 든든하게",
        display_url="samsungfire.com",
        image_url="https://drive.google.com/uc?id=abc",
    )
    assert len(row) == len(RAW_HEADERS)


def test_build_raw_row_values():
    row = build_raw_row(
        collected_at="2026-06-26 09:00",
        keyword="여행자보험",
        env="PC",
        rank=3,
        advertiser="삼성화재",
        headline="제목",
        description="설명",
        display_url="url.com",
        image_url="https://drive.google.com/uc?id=xyz",
    )
    assert row[0] == "2026-06-26 09:00"
    assert row[2] == "PC"
    assert row[3] == 3
    assert row[4] == "삼성화재"
    assert row[8] == '=IMAGE("https://drive.google.com/uc?id=xyz")'
