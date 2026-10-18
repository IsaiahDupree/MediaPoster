"""Unit tests for config.blotato_accounts, which now reads the account registry.

No network, no running server: these assert the mapping layer itself, which is
the part that decides WHICH BRAND a post lands on. The module previously held a
hand-transcribed list that was wrong on nine accounts and carried a YouTube
channel id with two lowercase 'l' where capital 'I' belonged; the existing
tests/test_blotato_accounts.py cannot catch that class of error because it holds
its own copy of the same transcription.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import blotato_accounts as ba  # noqa: E402


REGISTRY_AVAILABLE = ba.REGISTRY_PATH.exists()
requires_registry = pytest.mark.skipif(
    not REGISTRY_AVAILABLE,
    reason=f"account registry not present at {ba.REGISTRY_PATH}")


@requires_registry
def test_every_account_comes_from_the_registry():
    raw = json.loads(ba.REGISTRY_PATH.read_text())
    blotato_ids = set()
    for a in raw["accounts"]:
        for slot in ("credentials", "fallback"):
            c = a.get(slot) or {}
            if c.get("kind") == "blotato" and c.get("blotato_account_id"):
                blotato_ids.add(int(c["blotato_account_id"]))
                break
    assert {a.blotato_id for a in ba.BLOTATO_ACCOUNTS} == blotato_ids


@requires_registry
def test_no_blotato_id_is_claimed_by_two_accounts():
    """A duplicated id means two brands share one destination."""
    ids = [a.blotato_id for a in ba.BLOTATO_ACCOUNTS]
    assert len(ids) == len(set(ids)), "duplicate blotato_id in the mapping"


@requires_registry
def test_each_id_maps_to_exactly_one_platform():
    """The old hand-typed list had 4508 on both tiktok and instagram, and 243
    on both tiktok and pinterest. One Blotato account has one platform."""
    seen = {}
    for a in ba.BLOTATO_ACCOUNTS:
        assert seen.setdefault(a.blotato_id, a.platform) == a.platform


@requires_registry
def test_normalize_username_preserves_the_trailing_underscore():
    """@the_isaiah_dupree and @the_isaiah_dupree_ are different accounts.

    A normaliser that strips underscores maps one onto the other, which is how
    a post reaches the wrong brand. Verified against the real pair 2026-08-21.
    """
    assert ba.normalize_username("the_isaiah_dupree") != \
        ba.normalize_username("the_isaiah_dupree_")
    assert ba.normalize_username("@The_Isaiah_Dupree") == "the_isaiah_dupree"


@requires_registry
def test_the_near_identical_threads_handles_resolve_separately():
    with_us = ba.lookup_blotato_id("threads", "the_isaiah_dupree_")
    without = ba.lookup_blotato_id("threads", "the_isaiah_dupree")
    assert with_us is not None and without is not None
    assert with_us != without, "the two Threads accounts collapsed onto one id"


@requires_registry
def test_lookup_is_at_sign_and_case_insensitive():
    plain = ba.lookup_blotato_id("tiktok", "isaiah_dupree")
    assert plain is not None
    assert ba.lookup_blotato_id("tiktok", "@isaiah_dupree") == plain
    assert ba.lookup_blotato_id("TikTok", "Isaiah_Dupree") == plain


@requires_registry
def test_unknown_lookups_return_none_rather_than_a_default():
    """Falling back to a platform default is exactly the bug being removed."""
    assert ba.lookup_blotato_id("tiktok", "no_such_user") is None
    assert ba.get_blotato_id("nosuchplatform", "isaiah_dupree") is None
    assert ba.get_blotato_account("tiktok", "no_such_user") is None


@requires_registry
def test_platform_names_are_blotato_vocabulary_not_registry_vocabulary():
    """The registry says youtube_shorts / instagram_reels / x; Blotato says
    youtube / instagram / twitter. Publishing with the wrong one is rejected."""
    platforms = {a.platform for a in ba.BLOTATO_ACCOUNTS}
    assert not platforms & {"youtube_shorts", "instagram_reels",
                            "facebook_reels", "x"}
    assert platforms <= {"youtube", "instagram", "facebook", "twitter",
                         "tiktok", "threads", "pinterest"}


@requires_registry
def test_a_missing_registry_yields_empty_not_a_stale_guess(monkeypatch, tmp_path):
    monkeypatch.setattr(ba, "REGISTRY_PATH", tmp_path / "nope.json")
    assert ba._load_registry() == []


@requires_registry
def test_get_all_accounts_for_platform_excludes_non_publishable():
    for a in ba.get_all_accounts_for_platform("tiktok"):
        assert a.is_active
