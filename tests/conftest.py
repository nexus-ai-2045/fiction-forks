"""すべてのtestが本checkoutの`src/`を見ることを保証するsys.path bootstrap。

pytestはtest moduleより先にconftestをimportするため、collect順に依存せず
`src/`をsys.pathの先頭へ置ける。これが無いと、editable installが別checkoutを
指している環境で単独実行したtestが無言でstale packageを検証してしまう。
CIは`PYTHONPATH=src`付きの`unittest discover`で回すため、この file を読まない。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
