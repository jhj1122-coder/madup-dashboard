# scraper.py
from dataclasses import dataclass
from typing import Optional
from playwright.sync_api import sync_playwright, Locator, Page
from config import PC_UA, MOBILE_UA, NAVER_SEARCH_URL


@dataclass
class AdItem:
    rank: int
    advertiser: str
    headline: str
    description: str
    display_url: str
    screenshot_bytes: bytes

    def is_target_brand(self, brand: str) -> bool:
        return brand in self.advertiser


def _extract_ad_item(locator: Locator, rank: int) -> Optional[AdItem]:
    try:
        advertiser = ""
        for sel in [".site", ".tit_wrap .site_name", ".link_tit", "a[class*='tit']", ".tit_area a", ".site_name"]:
            el = locator.locator(sel).first
            if el.count() > 0:
                advertiser = el.inner_text().strip()
                break

        headline = ""
        for sel in [".lnk_tit", ".tit_wrap .tit", ".tit", "a.tit", ".link_tit"]:
            el = locator.locator(sel).first
            if el.count() > 0:
                headline = el.inner_text().strip()
                break
        if not headline:
            headline = advertiser

        description = ""
        for sel in [".desc_area", ".dsc_area .dsc", ".dsc_txt", "[class*='dsc']", "[class*='desc']"]:
            el = locator.locator(sel).first
            if el.count() > 0:
                description = el.inner_text().strip()
                break

        display_url = ""
        for sel in [".lnk_url", ".url_area .url", ".url", "[class*='url']"]:
            el = locator.locator(sel).first
            if el.count() > 0:
                display_url = el.inner_text().strip()
                break

        screenshot_bytes = locator.screenshot()

        return AdItem(
            rank=rank,
            advertiser=advertiser,
            headline=headline,
            description=description,
            display_url=display_url,
            screenshot_bytes=screenshot_bytes,
        )
    except Exception:
        return None


def parse_ad_items(container: Locator) -> list[AdItem]:
    items = []
    count = container.count()
    for i in range(count):
        item = _extract_ad_item(container.nth(i), rank=i + 1)
        if item:
            items.append(item)
    return items


def _get_ad_container(page: Page) -> Optional[Locator]:
    for sel in [
        ".nad_area .lst_type > li",
        "#power_link_body li.lst",
        "#power_link_body li",
        ".nad_area li",
        "#sp_npad ul > li",
        ".lst_ad > li",
        "[id*='ad'] ul > li",
        "ul.lst_ad li",
        "#sp_npad li",
        ".lst_ad li",
        "[class*='power_link'] li",
        ".ad_area li",
    ]:
        loc = page.locator(sel)
        if loc.count() > 0:
            return loc
    return None


_CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"


def scrape_keyword(keyword: str, env: str) -> list[AdItem]:
    import os
    is_mobile = env == "모바일"
    ua = MOBILE_UA if is_mobile else PC_UA

    with sync_playwright() as p:
        launch_kwargs = dict(headless=True, args=["--no-sandbox"])
        if os.path.exists(_CHROME_PATH):
            launch_kwargs["executable_path"] = _CHROME_PATH
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 390, "height": 844} if is_mobile else {"width": 1280, "height": 800},
        )
        page = context.new_page()
        url = NAVER_SEARCH_URL.format(keyword=keyword)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        container = _get_ad_container(page)
        if container is None:
            browser.close()
            return []

        items = parse_ad_items(container)
        browser.close()
        return items
