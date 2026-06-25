from datetime import datetime, timezone, timedelta
import pytest
from calculator import calc_work_hours, calc_resource_pct, check_special_leave

KST = timezone(timedelta(hours=9))


def kst(hour, minute=0, day=25):
    return datetime(2026, 6, day, hour, minute, tzinfo=KST)


class TestCalcWorkHours:
    def test_normal_day(self):
        # 09:00 출근 ~ 18:00 퇴근 → 9h - 1h = 8h
        assert calc_work_hours(kst(9, 0), kst(18, 0)) == 8.0

    def test_late_checkout_midnight(self):
        # 09:00 출근 ~ 다음날 02:30 퇴근 (new day=26) → 17.5h - 1h = 16.5h
        checkout = datetime(2026, 6, 26, 2, 30, tzinfo=KST)
        assert calc_work_hours(kst(9, 0), checkout) == 16.5

    def test_missing_checkin(self):
        assert calc_work_hours(None, kst(18, 0)) is None

    def test_missing_checkout(self):
        assert calc_work_hours(kst(9, 0), None) is None

    def test_fractional_hours(self):
        # 09:30 ~ 19:00 → 9.5h - 1h = 8.5h
        assert calc_work_hours(kst(9, 30), kst(19, 0)) == 8.5


class TestCalcResourcePct:
    def test_under_32(self):
        assert calc_resource_pct(31.9) == "80%+"

    def test_32_to_36(self):
        assert calc_resource_pct(34.0) == "80%+"

    def test_36_to_40(self):
        assert calc_resource_pct(38.0) == "90%+"

    def test_40_to_44(self):
        assert calc_resource_pct(42.0) == "100%+"

    def test_44_to_48(self):
        assert calc_resource_pct(46.0) == "110%+"

    def test_48_to_52(self):
        assert calc_resource_pct(50.0) == "120%+"

    def test_52_or_more(self):
        assert calc_resource_pct(52.0) == "130%+"

    def test_exactly_36(self):
        assert calc_resource_pct(36.0) == "90%+"

    def test_exactly_40(self):
        assert calc_resource_pct(40.0) == "100%+"


class TestCheckSpecialLeave:
    def _lunch_time(self, hour, minute=0):
        # lunch_time = 점심 스레드 리플 timestamp
        return kst(hour, minute)

    def test_case1_all_conditions_met(self):
        # 사무실, 15h 이상, 점심 13:00(복귀 14:00 이전)
        result = check_special_leave("사무실", 15.0, False, self._lunch_time(12, 50))
        assert result == "CASE1"

    def test_case1_jeonya_also_qualifies(self):
        # 전야재는 사무실 포함
        result = check_special_leave("전야재", 15.0, True, self._lunch_time(12, 50))
        # 전야재이면서 15h+ → CASE2도 될 수 있지만 CASE2 조건 먼저: 11h+ OK, so CASE2
        # 여기서는 CASE2도 충족하므로 CASE2 반환 (전야재 우선)
        assert result == "CASE2"

    def test_case1_fails_no_office(self):
        result = check_special_leave("재택", 15.0, False, self._lunch_time(12, 50))
        assert result is None

    def test_case1_fails_under_15h(self):
        result = check_special_leave("사무실", 14.9, False, self._lunch_time(12, 50))
        assert result is None

    def test_case1_fails_lunch_too_late(self):
        # 점심 13:01 → 복귀 14:01 > 14:00 → 특휴 없음
        result = check_special_leave("사무실", 15.0, False, self._lunch_time(13, 1))
        assert result is None

    def test_case1_no_lunch_record(self):
        # 점심 기록 없으면 14시 룰 위반 없음 → 조건 충족 시 특휴
        result = check_special_leave("사무실", 15.0, False, None)
        assert result == "CASE1"

    def test_case2_all_conditions_met(self):
        result = check_special_leave("전야재", 11.0, True, self._lunch_time(12, 50))
        assert result == "CASE2"

    def test_case2_fails_not_jeonya(self):
        result = check_special_leave("사무실", 11.0, False, self._lunch_time(12, 50))
        assert result is None

    def test_case2_fails_under_11h(self):
        result = check_special_leave("전야재", 10.9, True, self._lunch_time(12, 50))
        assert result is None

    def test_case2_fails_lunch_too_late(self):
        result = check_special_leave("전야재", 11.0, True, self._lunch_time(13, 1))
        assert result is None
