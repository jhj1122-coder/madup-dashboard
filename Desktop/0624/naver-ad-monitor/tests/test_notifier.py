# tests/test_notifier.py
import pytest
from notifier import build_alert_message, should_alert


def test_should_alert_rank_out_of_range():
    assert should_alert(rank=1) is True
    assert should_alert(rank=3) is True
    assert should_alert(rank=4) is False
    assert should_alert(rank=5) is False
    assert should_alert(rank=6) is True


def test_should_alert_not_found():
    assert should_alert(rank=None) is True


def test_build_alert_message_out_of_range():
    msg = build_alert_message(keyword="여행자보험", env="PC", rank=2, collected_at="2026-06-26 09:00")
    assert "여행자보험" in msg
    assert "PC" in msg
    assert "2위" in msg


def test_build_alert_message_not_found():
    msg = build_alert_message(keyword="해외여행보험", env="모바일", rank=None, collected_at="2026-06-26 09:30")
    assert "미노출" in msg
