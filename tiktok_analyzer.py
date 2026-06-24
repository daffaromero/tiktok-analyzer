"""TikTok hashtag/video analyzer — collection + tidy-table logic.

Pure helpers (ID parsing, VTT parsing, record extraction, summary, export) are
unit-tested. The async collection layer at the bottom talks to TikTok and is
verified by manual smoke test.
"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Subtitle languages to prefer, in order, when a video has several.
PREFERRED_SUBTITLE_LANGS = ["eng-US", "en", "eng", "ind", "id"]


_VIDEO_URL_RE = re.compile(r"/video/(\d+)")
_BARE_ID_RE = re.compile(r"^\d{6,}$")


def normalize_video_id(value: str) -> Optional[str]:
    """Extract the numeric video id from a URL or bare id. None if not derivable."""
    if value is None:
        return None
    text = str(value).strip()
    m = _VIDEO_URL_RE.search(text)
    if m:
        return m.group(1)
    if _BARE_ID_RE.match(text):
        return text
    return None


def parse_video_ids(values: List[str]) -> List[str]:
    """Normalize a list of ids/URLs, drop invalid, dedupe preserving order."""
    out: "OrderedDict[str, None]" = OrderedDict()
    for v in values or []:
        vid = normalize_video_id(v)
        if vid is not None:
            out[vid] = None
    return list(out.keys())


def merge_video_ids(discovered: List[str], explicit: List[str]) -> List[str]:
    """Merge two id lists, dedupe preserving order (discovered first)."""
    out: "OrderedDict[str, None]" = OrderedDict()
    for vid in list(discovered or []) + list(explicit or []):
        out[vid] = None
    return list(out.keys())


_TS_RE = re.compile(r"-->")
_TAG_RE = re.compile(r"<[^>]+>")


def vtt_to_text(raw: str) -> str:
    """Convert WebVTT (or SRT-ish) subtitle text to a single plain string."""
    if not raw:
        return ""
    lines: List[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "WEBVTT" or s.startswith("WEBVTT"):
            continue
        if _TS_RE.search(s):
            continue
        if s.isdigit():  # cue index
            continue
        s = _TAG_RE.sub("", s).strip()
        if not s:
            continue
        if lines and lines[-1] == s:  # collapse consecutive duplicates
            continue
        lines.append(s)
    return " ".join(lines)


_HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "]",
    flags=re.UNICODE,
)


def extract_hashtags(desc: str) -> List[str]:
    if not desc:
        return []
    out: "OrderedDict[str, None]" = OrderedDict()
    for tag in _HASHTAG_RE.findall(desc):
        out[tag.lower()] = None
    return list(out.keys())


def extract_emojis(text: str) -> List[str]:
    if not text:
        return []
    return _EMOJI_RE.findall(text)


def video_record(d: dict, has_subtitles: bool) -> dict:
    d = d or {}
    stats = d.get("stats") or {}
    author = (d.get("author") or {}).get("uniqueId", "")
    vid = str(d.get("id", ""))
    desc = d.get("desc", "") or ""
    url = ""
    if author and vid:
        url = "https://www.tiktok.com/@{}/video/{}".format(author, vid)
    return {
        "video_id": vid,
        "url": url,
        "author": author,
        "caption": desc,
        "created": d.get("createTime", ""),
        "likes": stats.get("diggCount", 0) or 0,
        "comment_count": stats.get("commentCount", 0) or 0,
        "share_count": stats.get("shareCount", 0) or 0,
        "play_count": stats.get("playCount", 0) or 0,
        "hashtags": ", ".join(extract_hashtags(desc)),
        "has_subtitles": bool(has_subtitles),
    }


def comment_record(c: dict, video_id: str) -> dict:
    c = c or {}
    user = c.get("user") or {}
    return {
        "video_id": str(video_id),
        "comment_id": str(c.get("cid", "")),
        "text": c.get("text", "") or "",
        "likes": c.get("digg_count", 0) or 0,
        "reply_count": c.get("reply_comment_total", 0) or 0,
        "author": user.get("unique_id", "") or "",
        "created": c.get("create_time", ""),
    }
