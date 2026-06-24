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


def test_extract_hashtags():
    assert ta.extract_hashtags("Love #Coffee and #coffee #Latte!") == ["coffee", "latte"]


def test_extract_hashtags_none():
    assert ta.extract_hashtags("") == []


def test_extract_emojis():
    assert ta.extract_emojis("nice ☕ day 🎉🎉") == ["☕", "🎉", "🎉"]


VIDEO_AS_DICT = {
    "id": "7251234567890123456",
    "desc": "morning #coffee ☕",
    "createTime": 1700000000,
    "author": {"uniqueId": "barista_jo"},
    "stats": {"diggCount": 1200, "commentCount": 45, "shareCount": 8, "playCount": 99000},
}


def test_video_record():
    rec = ta.video_record(VIDEO_AS_DICT, has_subtitles=True)
    assert rec["video_id"] == "7251234567890123456"
    assert rec["author"] == "barista_jo"
    assert rec["caption"] == "morning #coffee ☕"
    assert rec["likes"] == 1200
    assert rec["comment_count"] == 45
    assert rec["share_count"] == 8
    assert rec["play_count"] == 99000
    assert rec["hashtags"] == "coffee"
    assert rec["has_subtitles"] is True
    assert rec["url"] == "https://www.tiktok.com/@barista_jo/video/7251234567890123456"


def test_video_record_missing_fields():
    rec = ta.video_record({"id": "123456"}, has_subtitles=False)
    assert rec["video_id"] == "123456"
    assert rec["author"] == ""
    assert rec["likes"] == 0
    assert rec["hashtags"] == ""


COMMENT_AS_DICT = {
    "cid": "999",
    "text": "love this 🎉",
    "digg_count": 17,
    "reply_comment_total": 2,
    "create_time": 1700000500,
    "user": {"unique_id": "fan_a"},
}


def test_comment_record():
    rec = ta.comment_record(COMMENT_AS_DICT, "7251234567890123456")
    assert rec["video_id"] == "7251234567890123456"
    assert rec["comment_id"] == "999"
    assert rec["text"] == "love this 🎉"
    assert rec["likes"] == 17
    assert rec["reply_count"] == 2
    assert rec["author"] == "fan_a"
    assert rec["created"] == 1700000500


def test_comment_record_missing_fields():
    rec = ta.comment_record({"cid": "1"}, "123")
    assert rec["text"] == ""
    assert rec["likes"] == 0
    assert rec["author"] == ""


def test_build_videos_df_columns_and_empty():
    df = ta.build_videos_df([])
    assert list(df.columns) == ta.VIDEO_COLUMNS
    assert len(df) == 0


def test_build_videos_df_rows():
    rec = ta.video_record(VIDEO_AS_DICT, has_subtitles=False)
    df = ta.build_videos_df([rec])
    assert len(df) == 1
    assert df.iloc[0]["video_id"] == "7251234567890123456"
    assert list(df.columns) == ta.VIDEO_COLUMNS


def test_build_comments_df_columns():
    df = ta.build_comments_df([])
    assert list(df.columns) == ta.COMMENT_COLUMNS


def test_build_subtitles_df():
    df = ta.build_subtitles_df([{"video_id": "1", "lang": "eng-US", "text": "hello"}])
    assert list(df.columns) == ta.SUBTITLE_COLUMNS
    assert df.iloc[0]["text"] == "hello"


def test_build_summary_top_hashtags_and_comments():
    videos = ta.build_videos_df([
        ta.video_record({"id": "1", "desc": "#coffee #tea", "author": {"uniqueId": "a"},
                          "stats": {"diggCount": 1}}, False),
        ta.video_record({"id": "2", "desc": "#coffee", "author": {"uniqueId": "b"},
                         "stats": {"diggCount": 1}}, False),
    ])
    comments = ta.build_comments_df([
        ta.comment_record({"cid": "1", "text": "great", "digg_count": 50}, "1"),
        ta.comment_record({"cid": "2", "text": "ok", "digg_count": 5}, "1"),
    ])
    summary = ta.build_summary_df(videos, comments, top_n=5)
    assert list(summary.columns) == ["section", "item", "value"]
    hashtags = summary[summary["section"] == "top_hashtags"]
    top = hashtags.iloc[0]
    assert top["item"] == "coffee" and top["value"] == 2
    top_comments = summary[summary["section"] == "top_comments"]
    assert top_comments.iloc[0]["item"] == "great"


def test_build_summary_handles_empty():
    summary = ta.build_summary_df(ta.build_videos_df([]), ta.build_comments_df([]))
    assert list(summary.columns) == ["section", "item", "value"]
