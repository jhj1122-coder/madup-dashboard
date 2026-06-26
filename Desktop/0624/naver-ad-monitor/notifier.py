# notifier.py
import os
import requests
from typing import Optional
from config import TARGET_BRAND, TARGET_RANK_MIN, TARGET_RANK_MAX


def should_alert(rank: Optional[int]) -> bool:
    if rank is None:
        return True
    return not (TARGET_RANK_MIN <= rank <= TARGET_RANK_MAX)


def build_alert_message(keyword: str, env: str, rank: Optional[int], collected_at: str) -> str:
    rank_str = f"{rank}위" if rank is not None else "미노출"
    status = "⚠️ 순위 이탈" if rank is not None else "🚨 광고 미노출"
    return (
        f"{status} | {TARGET_BRAND} 파워링크\n"
        f"🔍 키워드: {keyword} ({env})\n"
        f"📊 현재 순위: {rank_str} (목표: {TARGET_RANK_MIN}~{TARGET_RANK_MAX}위)\n"
        f"🕐 수집시간: {collected_at}"
    )


def send_slack_alert(keyword: str, env: str, rank: Optional[int], collected_at: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    message = build_alert_message(keyword, env, rank, collected_at)
    response = requests.post(webhook_url, json={"text": message}, timeout=10)
    if response.status_code != 200:
        print(f"[notifier] Slack webhook error: {response.status_code} {response.text}")
