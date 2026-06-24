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


VIDEO_COLUMNS = [
    "video_id", "url", "author", "caption", "created",
    "likes", "comment_count", "share_count", "play_count",
    "hashtags", "has_subtitles",
]
COMMENT_COLUMNS = [
    "video_id", "comment_id", "text", "likes", "reply_count", "author", "created",
]
SUBTITLE_COLUMNS = ["video_id", "lang", "text"]

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is",
    "it", "this", "that", "i", "you", "so", "my", "me", "we", "be", "are", "was",
    "with", "at", "as", "if", "im", "its", "do", "not", "no", "yes",
}


def _df(records: List[dict], columns: List[str]) -> pd.DataFrame:
    df = pd.DataFrame(records or [], columns=columns)
    return df.reindex(columns=columns)


def build_videos_df(records: List[dict]) -> pd.DataFrame:
    return _df(records, VIDEO_COLUMNS)


def build_comments_df(records: List[dict]) -> pd.DataFrame:
    return _df(records, COMMENT_COLUMNS)


def build_subtitles_df(records: List[dict]) -> pd.DataFrame:
    return _df(records, SUBTITLE_COLUMNS)


def _counter_rows(section: str, counter: Counter, top_n: int) -> List[dict]:
    return [
        {"section": section, "item": item, "value": count}
        for item, count in counter.most_common(top_n)
    ]


def build_summary_df(videos_df: pd.DataFrame, comments_df: pd.DataFrame,
                     top_n: int = 15) -> pd.DataFrame:
    rows: List[dict] = []

    hashtag_counter: Counter = Counter()
    for cell in videos_df.get("hashtags", pd.Series(dtype=str)).fillna(""):
        for tag in [t.strip() for t in str(cell).split(",") if t.strip()]:
            hashtag_counter[tag] += 1
    rows += _counter_rows("top_hashtags", hashtag_counter, top_n)

    emoji_counter: Counter = Counter()
    word_counter: Counter = Counter()
    for cell in comments_df.get("text", pd.Series(dtype=str)).fillna(""):
        text = str(cell)
        emoji_counter.update(extract_emojis(text))
        for w in _WORD_RE.findall(text.lower()):
            if len(w) > 2 and w not in _STOPWORDS:
                word_counter[w] += 1
    rows += _counter_rows("top_emojis", emoji_counter, top_n)
    rows += _counter_rows("top_words", word_counter, top_n)

    if len(comments_df) and "likes" in comments_df:
        top_comments = comments_df.sort_values("likes", ascending=False).head(top_n)
        for _, c in top_comments.iterrows():
            rows.append({"section": "top_comments", "item": c.get("text", ""),
                         "value": c.get("likes", 0)})

    return pd.DataFrame(rows, columns=["section", "item", "value"])


def export_workbook(tables: Dict[str, pd.DataFrame], out_dir: str,
                    source_label: str, date_str: str) -> str:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    xlsx_path = out / "tiktok_{}_{}.xlsx".format(source_label, date_str)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for sheet, df in tables.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)

    for key, df in tables.items():
        csv_path = out / "{}_{}_{}.csv".format(source_label, date_str, key)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return str(xlsx_path.resolve())


# --- Async collection layer (network; verified by manual smoke test) ---------
import asyncio  # noqa: E402

import httpx  # noqa: E402


def pick_subtitle_info(subtitle_infos: List[dict]) -> Optional[dict]:
    """Pick the best subtitle entry by preferred language, else the first."""
    if not subtitle_infos:
        return None
    def rank(info: dict) -> int:
        lang = info.get("LanguageCodeName", "")
        return (PREFERRED_SUBTITLE_LANGS.index(lang)
                if lang in PREFERRED_SUBTITLE_LANGS else len(PREFERRED_SUBTITLE_LANGS))
    return sorted(subtitle_infos, key=rank)[0]


def _subtitle_url(info: dict) -> str:
    if not info:
        return ""
    if info.get("Url"):
        return info["Url"]
    url_list = info.get("UrlList") or []
    return url_list[0] if url_list else ""


async def _http_get_text(url: str) -> str:
    """Default subtitle downloader."""
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_subtitle(as_dict: dict, http_get=_http_get_text) -> Optional[dict]:
    """Return {'lang','text'} for the best available subtitle, or None."""
    video_meta = (as_dict or {}).get("video") or {}
    infos = video_meta.get("subtitleInfos") or []
    info = pick_subtitle_info(infos)
    url = _subtitle_url(info)
    if not url:
        return None
    try:
        raw = await http_get(url)
    except Exception:
        return None
    text = vtt_to_text(raw)
    if not text:
        return None
    return {"lang": info.get("LanguageCodeName", ""), "text": text}


async def _create_api(ms_token: Optional[str], log):
    """Create a TikTokApi session. Tries auto ms_token, then provided token."""
    from TikTokApi import TikTokApi  # imported lazily so unit tests need no install
    api = TikTokApi()
    tokens = [ms_token] if ms_token else None
    await api.create_sessions(ms_tokens=tokens, num_sessions=1, sleep_after=3,
                              browser="chromium", headless=True)
    log("TikTok session created.")
    return api


async def _discover_hashtag_ids(api, hashtag: str, max_videos: int, log) -> List[str]:
    ids: List[str] = []
    if not hashtag:
        return ids
    log("Discovering videos for #{} ...".format(hashtag))
    tag = api.hashtag(name=hashtag)
    async for video in tag.videos(count=max_videos):
        ids.append(str(video.id))
    log("Discovered {} videos.".format(len(ids)))
    return ids


async def collect(config: dict, log=print) -> Dict[str, pd.DataFrame]:
    """Top-level orchestration. config keys:
        hashtag, video_ids, max_videos, comments_per_video, ms_token, sleep_seconds.
    Returns {'Videos','Comments','Subtitles','Summary'} DataFrames.
    """
    hashtag = (config.get("hashtag") or "").strip().lstrip("#")
    explicit_ids = parse_video_ids(config.get("video_ids") or [])
    max_videos = int(config.get("max_videos", 30))
    comments_per_video = int(config.get("comments_per_video", 50))
    ms_token = config.get("ms_token") or None
    sleep_seconds = float(config.get("sleep_seconds", 2))

    video_records: List[dict] = []
    comment_records: List[dict] = []
    subtitle_records: List[dict] = []

    api = await _create_api(ms_token, log)
    try:
        discovered = await _discover_hashtag_ids(api, hashtag, max_videos, log)
        target_ids = merge_video_ids(discovered, explicit_ids)
        log("Fetching {} unique videos...".format(len(target_ids)))

        for i, vid in enumerate(target_ids, 1):
            try:
                video = api.video(id=vid)
                as_dict = await video.info()

                sub = await fetch_subtitle(as_dict)
                video_records.append(video_record(as_dict, has_subtitles=bool(sub)))
                if sub:
                    subtitle_records.append(
                        {"video_id": vid, "lang": sub["lang"], "text": sub["text"]})

                async for c in video.comments(count=comments_per_video):
                    comment_records.append(comment_record(c.as_dict, vid))

                log("[{}/{}] {} — {} comments, subtitles: {}".format(
                    i, len(target_ids), vid,
                    sum(1 for r in comment_records if r["video_id"] == vid),
                    "yes" if sub else "no"))
            except Exception as e:  # one bad video must not kill the run
                log("[{}/{}] {} — SKIPPED ({})".format(i, len(target_ids), vid, e))
            await asyncio.sleep(sleep_seconds)
    finally:
        try:
            await api.close_sessions()
        except Exception:
            pass

    videos_df = build_videos_df(video_records)
    comments_df = build_comments_df(comment_records)
    subtitles_df = build_subtitles_df(subtitle_records)
    summary_df = build_summary_df(videos_df, comments_df)
    return {"Videos": videos_df, "Comments": comments_df,
            "Subtitles": subtitles_df, "Summary": summary_df}
