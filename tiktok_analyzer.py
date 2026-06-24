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
