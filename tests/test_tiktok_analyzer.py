import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tiktok_analyzer as ta


def test_module_imports():
    assert ta.PREFERRED_SUBTITLE_LANGS[0] == "eng-US"


def test_normalize_full_url():
    url = "https://www.tiktok.com/@someuser/video/7251234567890123456"
    assert ta.normalize_video_id(url) == "7251234567890123456"


def test_normalize_url_with_query():
    url = "https://www.tiktok.com/@u/video/7251234567890123456?is_copy_url=1"
    assert ta.normalize_video_id(url) == "7251234567890123456"


def test_normalize_bare_id():
    assert ta.normalize_video_id("7251234567890123456") == "7251234567890123456"


def test_normalize_short_link_returns_none():
    assert ta.normalize_video_id("https://vm.tiktok.com/ZMabc123/") is None


def test_normalize_garbage_returns_none():
    assert ta.normalize_video_id("not a video") is None


def test_parse_video_ids_dedupes_and_drops_invalid():
    out = ta.parse_video_ids([
        "7251234567890123456",
        "https://www.tiktok.com/@u/video/7251234567890123456",  # dup
        "garbage",
        "7259999999999999999",
    ])
    assert out == ["7251234567890123456", "7259999999999999999"]


def test_merge_video_ids_preserves_order_no_dups():
    assert ta.merge_video_ids(["1", "2"], ["2", "3"]) == ["1", "2", "3"]
