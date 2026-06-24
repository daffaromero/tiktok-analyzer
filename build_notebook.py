"""Generates TikTok_Analyzer.ipynb. The module-embedding cell is the verbatim
contents of tiktok_analyzer.py so the notebook is self-contained on Colab."""
from pathlib import Path
import nbformat as nbf

here = Path(__file__).resolve().parent
module_src = (here / "tiktok_analyzer.py").read_text(encoding="utf-8")

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
    "# TikTok Analyzer\n"
    "Run cells top-to-bottom. Edit only the **CONFIG** cell.\n\n"
    "Collects comments, captions, and subtitles by hashtag/search or video ID/URL, "
    "then exports an Excel workbook (Videos / Comments / Subtitles / Summary) + CSVs.\n\n"
    "> Subtitles only exist for videos TikTok auto-captioned; others show blank."))

# 1. Setup — auto-detect Colab vs local
cells.append(nbf.v4.new_code_cell(
    "import sys\n"
    "IN_COLAB = 'google.colab' in sys.modules\n"
    "# Run once per environment. Comment out after the first successful run.\n"
    "%pip install -q TikTokApi pandas openpyxl nest_asyncio httpx\n"
    "!playwright install chromium\n"
    "if IN_COLAB:\n"
    "    !playwright install-deps\n"
    "print('Setup done. Colab:', IN_COLAB)"))

# 2. Embed module (keeps the notebook self-contained on Colab)
cells.append(nbf.v4.new_code_cell(
    "%%writefile tiktok_analyzer.py\n" + module_src))

# 3. CONFIG — the only cell to edit
cells.append(nbf.v4.new_code_cell(
    "# ===================== CONFIG — EDIT THIS CELL ONLY =====================\n"
    "HASHTAG = \"coffee\"          # hashtag to search (no #). Leave \"\" to skip.\n"
    "VIDEO_IDS = [               # specific videos: paste IDs or full URLs. Optional.\n"
    "    # \"https://www.tiktok.com/@user/video/7251234567890123456\",\n"
    "]\n"
    "MAX_VIDEOS = 30             # cap on hashtag-discovered videos\n"
    "COMMENTS_PER_VIDEO = 50     # comments to pull per video\n"
    "MS_TOKEN = \"\"              # leave \"\" to auto-try; paste a real ms_token if blocked\n"
    "# ========================================================================\n"
    "config = dict(hashtag=HASHTAG, video_ids=VIDEO_IDS, max_videos=MAX_VIDEOS,\n"
    "              comments_per_video=COMMENTS_PER_VIDEO, ms_token=MS_TOKEN,\n"
    "              sleep_seconds=2)\n"
    "print('Config ready:', {k: v for k, v in config.items() if k != 'ms_token'})"))

# 4. Run collection
cells.append(nbf.v4.new_code_cell(
    "import nest_asyncio, asyncio\n"
    "nest_asyncio.apply()\n"
    "import tiktok_analyzer as ta\n"
    "try:\n"
    "    tables = asyncio.get_event_loop().run_until_complete(ta.collect(config))\n"
    "    print('\\nCollected:', {k: len(v) for k, v in tables.items()})\n"
    "except Exception as e:\n"
    "    print('Collection failed:', e)\n"
    "    print('\\nIf this looks like a block/empty result: open tiktok.com in your "
    "browser while logged in, copy the ms_token cookie value, paste it into MS_TOKEN "
    "in the CONFIG cell, re-run CONFIG and this cell.')\n"
    "    raise"))

# 5. Preview
cells.append(nbf.v4.new_code_cell(
    "tables['Videos'].head()"))

# 6. Export (+ Colab download)
cells.append(nbf.v4.new_code_cell(
    "import datetime\n"
    "date_str = datetime.date.today().isoformat()\n"
    "source_label = (HASHTAG or 'videos').replace(' ', '_')\n"
    "xlsx_path = ta.export_workbook(tables, 'output', source_label, date_str)\n"
    "print('Saved workbook:', xlsx_path)\n"
    "if IN_COLAB:\n"
    "    from google.colab import files\n"
    "    files.download(xlsx_path)\n"
    "else:\n"
    "    print('Open this file in Excel, or upload it to Google Sheets to share.')"))

nb["cells"] = cells
nbf.write(nb, str(here / "TikTok_Analyzer.ipynb"))
print("Wrote TikTok_Analyzer.ipynb")
