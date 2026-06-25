import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from slack_parser import parse_location, find_workflow_threads, extract_user_records

KST = timezone(timedelta(hours=9))


class TestParseLocation:
    def test_office(self):
        assert parse_location("안녕하세요 사무실 출근합니다") == ("사무실", False)

    def test_remote(self):
        assert parse_location("오늘 재택입니다") == ("재택", False)

    def test_half_remote(self):
        assert parse_location("오전재택 후 오후 사무실") == ("재택", False)

    def test_jeonya(self):
        assert parse_location("전야재 출근합니다") == ("전야재", True)

    def test_no_keyword(self):
        # 키워드 없으면 사무실로 처리
        assert parse_location("출근합니다~") == ("사무실", False)

    def test_jeonya_overrides_office(self):
        # 전야재 키워드 있으면 전야재 우선
        assert parse_location("전야재 사무실") == ("전야재", True)


class TestFindWorkflowThreads:
    def _make_msg(self, ts, text, reply_count=1):
        return {"ts": ts, "text": text, "reply_count": reply_count}

    def test_finds_checkin_thread(self):
        messages = [
            self._make_msg("1000.0001", "출근 기록"),
            self._make_msg("1000.0002", "점심 기록"),
            self._make_msg("1000.0003", "퇴근 기록"),
        ]
        result = find_workflow_threads(messages)
        assert result["checkin"] == "1000.0001"
        assert result["lunch"] == "1000.0002"
        assert result["checkout"] == "1000.0003"

    def test_missing_thread_returns_none(self):
        messages = [self._make_msg("1000.0001", "출근 기록")]
        result = find_workflow_threads(messages)
        assert result["checkin"] == "1000.0001"
        assert result["lunch"] is None
        assert result["checkout"] is None

    def test_ignores_no_reply(self):
        messages = [self._make_msg("1000.0001", "출근 기록", reply_count=0)]
        result = find_workflow_threads(messages)
        assert result["checkin"] is None

    def test_keyword_variants(self):
        messages = [
            self._make_msg("1.0", "오늘의 출근기록"),
            self._make_msg("2.0", "오늘의 점심기록"),
            self._make_msg("3.0", "오늘의 퇴근기록"),
        ]
        result = find_workflow_threads(messages)
        assert result["checkin"] == "1.0"
        assert result["lunch"] == "2.0"
        assert result["checkout"] == "3.0"


class TestExtractUserRecords:
    def _make_reply(self, user, ts, text="사무실"):
        return {"user": user, "ts": ts, "text": text}

    def test_first_reply_per_user(self):
        replies = [
            self._make_reply("U001", "1000.0001", "사무실"),
            self._make_reply("U001", "1000.0002", "재택"),  # 두 번째 → 무시
            self._make_reply("U002", "1000.0003", "재택"),
        ]
        result = extract_user_records(replies)
        assert result["U001"]["ts"] == "1000.0001"
        assert result["U002"]["ts"] == "1000.0003"

    def test_empty_replies(self):
        assert extract_user_records([]) == {}

    def test_bot_message_skipped(self):
        replies = [
            {"bot_id": "B001", "ts": "1000.0001", "text": "워크플로우"},
            self._make_reply("U001", "1000.0002", "사무실"),
        ]
        result = extract_user_records(replies)
        assert "B001" not in result
        assert "U001" in result
