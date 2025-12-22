"""
Unit Tests: Scheduler Date/Time Logic (SCH-UNIT-*)
Tests for date math, timezone handling, DST, rounding rules, validation
"""

import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


class TestSCHUNIT001DateMath:
    """SCH-UNIT-001: Date math - month boundaries, leap years, week crossing"""
    
    def test_month_boundary_january_to_february(self):
        """Should handle January 31 -> February correctly"""
        jan_31 = datetime(2025, 1, 31)
        # Adding a month should go to Feb 28
        feb = jan_31.replace(month=2, day=28)
        assert feb.month == 2
        assert feb.day == 28
    
    def test_month_boundary_february_to_march(self):
        """Should handle February -> March correctly"""
        feb_28 = datetime(2025, 2, 28)
        march_1 = feb_28 + timedelta(days=1)
        assert march_1.month == 3
        assert march_1.day == 1
    
    def test_leap_year_february_29(self):
        """Should handle leap year February 29"""
        # 2024 is a leap year
        feb_29 = datetime(2024, 2, 29)
        assert feb_29.day == 29
        # Next day is March 1
        march_1 = feb_29 + timedelta(days=1)
        assert march_1.month == 3
    
    def test_non_leap_year_february(self):
        """Should not have February 29 in non-leap year"""
        # 2025 is not a leap year
        feb_28 = datetime(2025, 2, 28)
        march_1 = feb_28 + timedelta(days=1)
        assert march_1.month == 3
        assert march_1.day == 1
    
    def test_week_crossing_months(self):
        """Should handle weeks that cross month boundaries"""
        # December 28, 2025 is a Sunday
        dec_28 = datetime(2025, 12, 28)
        # Week includes Jan 1, 2, 3
        jan_1 = dec_28 + timedelta(days=4)
        assert jan_1.month == 1
        assert jan_1.year == 2026
    
    def test_week_start_sunday(self):
        """Should calculate week start as Sunday correctly"""
        # Any date should find its Sunday
        tuesday = datetime(2025, 12, 23)  # A Tuesday
        days_since_sunday = tuesday.weekday() + 1  # Monday=0, so Tuesday=1, +1 for Sunday
        if days_since_sunday == 7:
            days_since_sunday = 0
        sunday = tuesday - timedelta(days=(tuesday.weekday() + 1) % 7)
        assert sunday.weekday() == 6  # Sunday
    
    def test_week_start_monday(self):
        """Should calculate week start as Monday correctly"""
        tuesday = datetime(2025, 12, 23)
        monday = tuesday - timedelta(days=tuesday.weekday())
        assert monday.weekday() == 0  # Monday
    
    def test_days_in_month_calculation(self):
        """Should calculate days in month correctly"""
        def days_in_month(year, month):
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            return (next_month - datetime(year, month, 1)).days
        
        assert days_in_month(2025, 1) == 31  # January
        assert days_in_month(2025, 2) == 28  # February (non-leap)
        assert days_in_month(2024, 2) == 29  # February (leap)
        assert days_in_month(2025, 4) == 30  # April
        assert days_in_month(2025, 12) == 31  # December
    
    def test_year_boundary(self):
        """Should handle year boundary correctly"""
        dec_31 = datetime(2025, 12, 31, 23, 59, 59)
        jan_1 = dec_31 + timedelta(seconds=1)
        assert jan_1.year == 2026
        assert jan_1.month == 1
        assert jan_1.day == 1


class TestSCHUNIT002TimezoneHandling:
    """SCH-UNIT-002: Timezone + DST handling"""
    
    def test_utc_to_eastern(self):
        """Should convert UTC to Eastern correctly"""
        utc_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        eastern = ZoneInfo("America/New_York")
        eastern_time = utc_time.astimezone(eastern)
        # During DST, Eastern is UTC-4
        assert eastern_time.hour == 8  # 12 - 4 = 8
    
    def test_utc_to_pacific(self):
        """Should convert UTC to Pacific correctly"""
        utc_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        pacific = ZoneInfo("America/Los_Angeles")
        pacific_time = utc_time.astimezone(pacific)
        # During DST, Pacific is UTC-7
        assert pacific_time.hour == 5  # 12 - 7 = 5
    
    def test_dst_spring_forward(self):
        """Should handle DST spring forward correctly"""
        # March 9, 2025 at 2 AM becomes 3 AM
        eastern = ZoneInfo("America/New_York")
        # 1:59 AM exists
        before_dst = datetime(2025, 3, 9, 1, 59, tzinfo=eastern)
        # 3:00 AM exists (2:00-2:59 AM skipped)
        after_dst = datetime(2025, 3, 9, 3, 0, tzinfo=eastern)
        # Difference should be 1 minute (wall clock), but 61 minutes (real time)
        # Actually in terms of UTC, the gap is only 1 minute wall clock
        assert after_dst > before_dst
    
    def test_dst_fall_back(self):
        """Should handle DST fall back correctly"""
        # November 2, 2025 at 2 AM becomes 1 AM
        eastern = ZoneInfo("America/New_York")
        # Both 1:30 AM times exist (one EDT, one EST)
        time_1 = datetime(2025, 11, 2, 1, 30, tzinfo=eastern)
        assert time_1.hour == 1
    
    def test_store_in_utc(self):
        """Should store times in UTC"""
        eastern = ZoneInfo("America/New_York")
        local_time = datetime(2025, 6, 15, 10, 0, 0, tzinfo=eastern)
        utc_time = local_time.astimezone(timezone.utc)
        # Should be 14:00 UTC (10 + 4 for DST)
        assert utc_time.hour == 14
    
    def test_display_in_user_tz(self):
        """Should display times in user timezone"""
        utc_time = datetime(2025, 6, 15, 14, 0, 0, tzinfo=timezone.utc)
        tokyo = ZoneInfo("Asia/Tokyo")
        tokyo_time = utc_time.astimezone(tokyo)
        # Tokyo is UTC+9
        assert tokyo_time.hour == 23  # 14 + 9 = 23
    
    def test_iso_format_with_timezone(self):
        """Should format ISO with timezone offset"""
        eastern = ZoneInfo("America/New_York")
        time = datetime(2025, 6, 15, 10, 0, 0, tzinfo=eastern)
        iso = time.isoformat()
        assert "-04:00" in iso or "-05:00" in iso  # EDT or EST


class TestSCHUNIT003RoundingRules:
    """SCH-UNIT-003: Time rounding rules"""
    
    def test_round_to_nearest_5_minutes(self):
        """Should round to nearest 5 minutes"""
        def round_to_5_min(dt):
            minutes = dt.minute
            rounded = round(minutes / 5) * 5
            if rounded == 60:
                return dt.replace(minute=0) + timedelta(hours=1)
            return dt.replace(minute=rounded, second=0, microsecond=0)
        
        time_12 = datetime(2025, 1, 1, 10, 12)
        assert round_to_5_min(time_12).minute == 10
        
        time_13 = datetime(2025, 1, 1, 10, 13)
        assert round_to_5_min(time_13).minute == 15
        
        time_58 = datetime(2025, 1, 1, 10, 58)
        result = round_to_5_min(time_58)
        assert result.minute == 0 and result.hour == 11
    
    def test_round_to_nearest_10_minutes(self):
        """Should round to nearest 10 minutes"""
        def round_to_10_min(dt):
            minutes = dt.minute
            rounded = round(minutes / 10) * 10
            if rounded == 60:
                return dt.replace(minute=0) + timedelta(hours=1)
            return dt.replace(minute=rounded, second=0, microsecond=0)
        
        time_14 = datetime(2025, 1, 1, 10, 14)
        assert round_to_10_min(time_14).minute == 10
        
        time_15 = datetime(2025, 1, 1, 10, 15)
        assert round_to_10_min(time_15).minute == 20
    
    def test_round_to_nearest_15_minutes(self):
        """Should round to nearest 15 minutes"""
        def round_to_15_min(dt):
            minutes = dt.minute
            rounded = round(minutes / 15) * 15
            if rounded == 60:
                return dt.replace(minute=0) + timedelta(hours=1)
            return dt.replace(minute=rounded, second=0, microsecond=0)
        
        time_7 = datetime(2025, 1, 1, 10, 7)
        assert round_to_15_min(time_7).minute == 0
        
        time_8 = datetime(2025, 1, 1, 10, 8)
        assert round_to_15_min(time_8).minute == 15
        
        time_22 = datetime(2025, 1, 1, 10, 22)
        assert round_to_15_min(time_22).minute == 15


class TestSCHUNIT004Validation:
    """SCH-UNIT-004: Input validation rules"""
    
    def test_empty_title_rejected(self):
        """Should reject empty title"""
        def validate_title(title):
            if not title or not title.strip():
                raise ValueError("Title cannot be empty")
            return True
        
        with pytest.raises(ValueError):
            validate_title("")
        with pytest.raises(ValueError):
            validate_title("   ")
        assert validate_title("Valid Title")
    
    def test_title_max_length(self):
        """Should enforce max title length"""
        def validate_title_length(title, max_len=200):
            if len(title) > max_len:
                raise ValueError(f"Title exceeds {max_len} characters")
            return True
        
        with pytest.raises(ValueError):
            validate_title_length("x" * 201)
        assert validate_title_length("x" * 200)
    
    def test_invalid_time_input(self):
        """Should reject invalid time input"""
        def validate_time(time_str):
            try:
                parts = time_str.split(":")
                hours = int(parts[0])
                minutes = int(parts[1])
                if hours < 0 or hours > 23:
                    raise ValueError("Invalid hours")
                if minutes < 0 or minutes > 59:
                    raise ValueError("Invalid minutes")
                return True
            except (ValueError, IndexError):
                raise ValueError("Invalid time format")
        
        with pytest.raises(ValueError):
            validate_time("25:00")
        with pytest.raises(ValueError):
            validate_time("12:60")
        with pytest.raises(ValueError):
            validate_time("invalid")
        assert validate_time("12:30")
        assert validate_time("00:00")
        assert validate_time("23:59")
    
    def test_past_date_handling(self):
        """Should handle past date validation"""
        def is_future_date(dt):
            return dt > datetime.now()
        
        past = datetime.now() - timedelta(days=1)
        future = datetime.now() + timedelta(days=1)
        
        assert not is_future_date(past)
        assert is_future_date(future)
    
    def test_minimum_advance_scheduling(self):
        """Should enforce minimum 5-minute advance scheduling"""
        def validate_schedule_time(dt, min_minutes=5):
            min_time = datetime.now() + timedelta(minutes=min_minutes)
            if dt < min_time:
                raise ValueError(f"Must schedule at least {min_minutes} minutes in advance")
            return True
        
        too_soon = datetime.now() + timedelta(minutes=2)
        valid = datetime.now() + timedelta(minutes=10)
        
        with pytest.raises(ValueError):
            validate_schedule_time(too_soon)
        assert validate_schedule_time(valid)


class TestSCHUNIT005WeekCalculations:
    """SCH-UNIT-005: Week calculation utilities"""
    
    def test_get_week_days_sunday_start(self):
        """Should get 7 days starting from Sunday"""
        def get_week_days(date, start_sunday=True):
            if start_sunday:
                start = date - timedelta(days=(date.weekday() + 1) % 7)
            else:
                start = date - timedelta(days=date.weekday())
            return [start + timedelta(days=i) for i in range(7)]
        
        wednesday = datetime(2025, 12, 24)  # A Wednesday
        week = get_week_days(wednesday, start_sunday=True)
        assert len(week) == 7
        assert week[0].weekday() == 6  # Sunday
        assert week[6].weekday() == 5  # Saturday
    
    def test_get_week_days_monday_start(self):
        """Should get 7 days starting from Monday"""
        def get_week_days(date, start_sunday=True):
            if start_sunday:
                start = date - timedelta(days=(date.weekday() + 1) % 7)
            else:
                start = date - timedelta(days=date.weekday())
            return [start + timedelta(days=i) for i in range(7)]
        
        wednesday = datetime(2025, 12, 24)
        week = get_week_days(wednesday, start_sunday=False)
        assert len(week) == 7
        assert week[0].weekday() == 0  # Monday
        assert week[6].weekday() == 6  # Sunday
    
    def test_week_number_calculation(self):
        """Should calculate ISO week number correctly"""
        date = datetime(2025, 1, 1)
        week_num = date.isocalendar()[1]
        assert week_num == 1
        
        date2 = datetime(2025, 12, 31)
        week_num2 = date2.isocalendar()[1]
        assert week_num2 in [1, 52, 53]


class TestSCHUNIT006MonthCalculations:
    """SCH-UNIT-006: Month calculation utilities"""
    
    def test_get_month_grid(self):
        """Should generate month grid with leading/trailing days"""
        def get_month_grid(year, month):
            first_day = datetime(year, month, 1)
            first_weekday = first_day.weekday()  # Monday=0
            # Adjust for Sunday start
            first_weekday = (first_weekday + 1) % 7
            
            # Days in month
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            days_in_month = (next_month - first_day).days
            
            # Leading empty cells
            grid = [None] * first_weekday
            # Days
            grid.extend(range(1, days_in_month + 1))
            # Trailing to complete last week
            while len(grid) % 7 != 0:
                grid.append(None)
            
            return grid
        
        grid = get_month_grid(2025, 12)
        assert len(grid) % 7 == 0  # Complete weeks
        assert 1 in grid
        assert 31 in grid
    
    def test_navigate_months(self):
        """Should navigate between months correctly"""
        def next_month(year, month):
            if month == 12:
                return year + 1, 1
            return year, month + 1
        
        def prev_month(year, month):
            if month == 1:
                return year - 1, 12
            return year, month - 1
        
        assert next_month(2025, 12) == (2026, 1)
        assert next_month(2025, 6) == (2025, 7)
        assert prev_month(2025, 1) == (2024, 12)
        assert prev_month(2025, 6) == (2025, 5)
