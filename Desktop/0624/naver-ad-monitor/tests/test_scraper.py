# tests/test_scraper.py
import pytest
from unittest.mock import MagicMock, patch
from scraper import parse_ad_items, AdItem


def test_parse_ad_items_returns_list_of_ad_items():
    mock_locator = MagicMock()
    mock_locator.count.return_value = 2

    def fake_nth(i):
        m = MagicMock()
        m.inner_text.return_value = f"광고주{i+1}\n제목{i+1}\n설명{i+1}\nexample.com"
        m.query_selector.return_value = MagicMock(inner_text=lambda: f"광고주{i+1}")
        m.screenshot.return_value = b"PNG_BYTES"
        return m

    mock_locator.nth = fake_nth

    with patch("scraper._extract_ad_item") as mock_extract:
        mock_extract.side_effect = lambda loc, rank: AdItem(
            rank=rank,
            advertiser=f"광고주{rank}",
            headline=f"제목{rank}",
            description=f"설명{rank}",
            display_url="example.com",
            screenshot_bytes=b"PNG_BYTES",
        )
        result = parse_ad_items(mock_locator)

    assert len(result) == 2
    assert result[0].rank == 1
    assert result[1].rank == 2
    assert result[0].advertiser == "광고주1"


def test_ad_item_is_target_brand():
    item = AdItem(
        rank=4,
        advertiser="삼성화재",
        headline="해외여행자보험",
        description="든든한 보장",
        display_url="samsungfire.com",
        screenshot_bytes=b"",
    )
    assert item.is_target_brand("삼성화재") is True
    assert item.is_target_brand("현대해상") is False
