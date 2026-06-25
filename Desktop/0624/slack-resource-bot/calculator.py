from datetime import datetime, timezone, timedelta
from typing import Optional

KST = timezone(timedelta(hours=9))


def calc_work_hours(checkin: Optional[datetime], checkout: Optional[datetime]) -> Optional[float]:
    if checkin is None or checkout is None:
        return None
    delta = (checkout - checkin).total_seconds() / 3600 - 1.0
    return round(delta * 2) / 2  # 30분 단위 반올림


def calc_resource_pct(weekly_hours: float) -> str:
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


def check_special_leave(
    location: str,
    work_hours: float,
    is_jeonya: bool,
    lunch_time: Optional[datetime],
) -> Optional[str]:
    # 점심 14시 룰: 점심 리플 + 1h > 14:00 이면 특휴 없음
    if lunch_time is not None:
        lunch_return = lunch_time + timedelta(hours=1)
        cutoff = lunch_time.replace(hour=14, minute=0, second=0, microsecond=0)
        if lunch_return > cutoff:
            return None

    # CASE2 — 전야재 우선 체크
    if is_jeonya and work_hours >= 11.0:
        return "CASE2"

    # CASE1 — 사무실 장시간 (전야재도 사무실 포함이지만 is_jeonya=True면 CASE2 우선)
    if location in ("사무실", "전야재") and not is_jeonya and work_hours >= 15.0:
        return "CASE1"

    return None
