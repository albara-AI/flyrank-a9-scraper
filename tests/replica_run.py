"""Run the real CLI against the offline replica, with the same flags as src/main.py.

    python tests/replica_run.py
    python tests/replica_run.py --inject-broken-url

Writes to .replica/ (git-ignored) so replica data can never leak into cache/ or output/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from config import Settings
from main import main
from replica import replica_session

if __name__ == "__main__":
    session, adapter = replica_session()
    settings = Settings(
        cache_dir=ROOT / ".replica" / "cache",
        output_dir=ROOT / ".replica" / "output",
        delay_seconds=0.0,       # nothing real to be polite to; delay logic is unit-tested
        retry_wait_seconds=0.0,
    )
    code = main(sys.argv[1:], session=session, settings=settings)
    print(f"[replica] requests that reached the site: {len(adapter.log)} | exit code: {code}")
    sys.exit(code)
