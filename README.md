# TikTok Analyzer

Collects TikTok **comments, captions, and subtitles** by hashtag/search or by video
ID/URL, and exports a multi-tab Excel workbook (Videos / Comments / Subtitles / Summary)
plus CSVs. Built for non-engineers — run `TikTok_Analyzer.ipynb` top-to-bottom in
**Google Colab** or **local Jupyter** and edit only the CONFIG cell.

## Quick start
1. Open `TikTok_Analyzer.ipynb` (Colab: upload it; local: `jupyter notebook`).
2. Run the **Setup** cell once (installs deps + a bundled Chromium, ~150MB first time).
3. In **CONFIG**, set `HASHTAG` and/or paste `VIDEO_IDS`. Leave `MS_TOKEN` blank to start.
4. Run All. The workbook downloads (Colab) or is saved under `output/` (local).

## If it gets blocked / returns nothing
TikTok throttles scraping. Get a real token:
1. Log in to tiktok.com in your browser.
2. DevTools → Application → Cookies → copy the value of `msToken`.
3. Paste it into `MS_TOKEN` in the CONFIG cell, re-run CONFIG + the collection cell.

## Subtitles
Only videos TikTok auto-captioned expose subtitles; others show blank
(`has_subtitles=False` in the Videos tab). Partial coverage is expected.

## Sharing
Open the `.xlsx` in Excel, or upload it to Google Drive and open with Google Sheets
(drag-and-drop import keeps the tabs).

## Development
Logic lives in `tiktok_analyzer.py`, unit-tested: `python -m pytest tests/ -v`.
The notebook embeds this module via `%%writefile`; after editing the module,
regenerate the notebook with `python build_notebook.py`.
