from datetime import datetime, timedelta, timezone

import pytest

from app import repository
from app.config import settings
from app.errors import QuotaExceededError
from app.services import usage


def test_estimate_tokens_is_an_overcount_not_an_undercount():
    # ~4 chars/token, and never zero -- a tiny string still costs something.
    assert usage.estimate_tokens("a" * 400) == 100
    assert usage.estimate_tokens("hi") == 1
    assert usage.estimate_tokens("") == 1


def test_resets_at_is_one_window_after_the_period_started():
    started = datetime(2026, 7, 17, 9, 0, tzinfo=timezone.utc)
    assert usage.resets_at(started) == started + timedelta(hours=settings.quota_window_hours)


def _fake_usage(monkeypatch, *, used: int, limit: int, started: datetime):
    monkeypatch.setattr(
        repository,
        "get_usage",
        lambda *, user_id: {
            "tokens_used": used,
            "tokens_limit": limit,
            "period_started_at": started,
        },
    )


def test_check_quota_allows_a_request_that_fits(monkeypatch):
    _fake_usage(monkeypatch, used=10, limit=1000, started=datetime.now(timezone.utc))
    usage.check_quota(user_id="u1", needed_tokens=990)  # exactly fits


def test_check_quota_blocks_a_request_that_would_exceed(monkeypatch):
    _fake_usage(monkeypatch, used=10, limit=1000, started=datetime.now(timezone.utc))
    with pytest.raises(QuotaExceededError):
        usage.check_quota(user_id="u1", needed_tokens=991)


def test_quota_error_tells_the_user_when_their_window_resets(monkeypatch):
    started = datetime(2026, 7, 17, 9, 0, tzinfo=timezone.utc)
    _fake_usage(monkeypatch, used=1000, limit=1000, started=started)
    with pytest.raises(QuotaExceededError) as excinfo:
        usage.check_quota(user_id="u1", needed_tokens=1)
    # A quota error is useless without a "come back at" -- assert it's in there.
    assert usage.resets_at(started).strftime("%Y-%m-%d %H:%M") in str(excinfo.value)


def test_record_usage_skips_the_write_when_there_is_nothing_to_record(monkeypatch):
    calls = []
    monkeypatch.setattr(
        repository, "add_tokens_used", lambda **kw: calls.append(kw)
    )
    usage.record_usage(user_id="u1", tokens=0)
    assert calls == []
    usage.record_usage(user_id="u1", tokens=5)
    assert calls == [{"user_id": "u1", "tokens": 5}]
