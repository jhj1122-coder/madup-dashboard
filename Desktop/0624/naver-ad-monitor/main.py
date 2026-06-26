# main.py
from datetime import datetime, timezone, timedelta
from typing import Optional
from config import KEYWORDS, ENVIRONMENTS, TARGET_BRAND, DRIVE_FOLDER_NAME
from scraper import scrape_keyword, AdItem
from drive_uploader import upload_screenshot
from sheets_writer import build_raw_row, append_raw_rows, refresh_summary
from notifier import should_alert, send_slack_alert

KST = timezone(timedelta(hours=9))


def run() -> None:
    collected_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    all_raw_rows: list[list] = []

    for keyword in KEYWORDS:
        for env in ENVIRONMENTS:
            print(f"[{collected_at}] 수집 중: {keyword} / {env}")
            try:
                items: list[AdItem] = scrape_keyword(keyword, env)
            except Exception as e:
                print(f"[main] scrape failed {keyword}/{env}: {e}")
                send_slack_alert(keyword, env, None, collected_at)
                continue

            samsung_rank: Optional[int] = None

            for item in items:
                filename = f"{collected_at.replace(':', '-')}_{keyword}_{env}_{item.rank}.png"
                try:
                    image_url = upload_screenshot(
                        item.screenshot_bytes, filename, DRIVE_FOLDER_NAME
                    )
                except Exception as e:
                    print(f"[main] Drive 업로드 실패: {e}")
                    image_url = ""

                row = build_raw_row(
                    collected_at=collected_at,
                    keyword=keyword,
                    env=env,
                    rank=item.rank,
                    advertiser=item.advertiser,
                    headline=item.headline,
                    description=item.description,
                    display_url=item.display_url,
                    image_url=image_url,
                )
                all_raw_rows.append(row)

                if item.is_target_brand(TARGET_BRAND):
                    samsung_rank = item.rank

            if should_alert(samsung_rank):
                send_slack_alert(keyword, env, samsung_rank, collected_at)
                print(f"  ⚠️ 알림 발송: {keyword}/{env} 삼성화재 순위={samsung_rank}")
            else:
                print(f"  ✅ {keyword}/{env} 삼성화재 {samsung_rank}위 (정상)")

    if all_raw_rows:
        append_raw_rows(all_raw_rows)
        refresh_summary(all_raw_rows)
    print(f"완료: {len(all_raw_rows)}행 기록")


if __name__ == "__main__":
    run()
