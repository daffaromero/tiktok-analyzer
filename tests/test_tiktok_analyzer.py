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


SAMPLE_VTT = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
hello everyone

2
00:00:02.000 --> 00:00:04.000
hello everyone

3
00:00:04.000 --> 00:00:06.000
welcome to <c>my</c> channel
"""


def test_vtt_to_text_basic():
    out = ta.vtt_to_text(SAMPLE_VTT)
    assert out == "hello everyone welcome to my channel"


def test_vtt_to_text_empty():
    assert ta.vtt_to_text("") == ""


def test_vtt_to_text_header_only():
    assert ta.vtt_to_text("WEBVTT\n\n") == ""
