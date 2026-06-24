import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tiktok_analyzer as ta


def test_module_imports():
    assert ta.PREFERRED_SUBTITLE_LANGS[0] == "eng-US"
