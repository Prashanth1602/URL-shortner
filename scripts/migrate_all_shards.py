"""
Run Alembic migrations across all configured shards.
Usage:
  python scripts/migrate_all_shards.py upgrade head
  python scripts/migrate_all_shards.py downgrade -1

This script iterates over SHARD_DB_URLS from app.core.config.settings and
executes Alembic for each shard by setting the DATABASE_URL env var.
"""
import os
import subprocess
import sys
from typing import List

# Ensure project root in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
os.chdir(PROJECT_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import settings, SHARD_DB_URL_LIST  # noqa: E402

def run_for_shard(db_url: str, alembic_args: List[str]) -> int:
    env = os.environ.copy()
    # Provide DATABASE_URL so alembic/env.py will use it
    env["DATABASE_URL"] = db_url
    print(f"\n=== Running Alembic for shard: {db_url} ===")
    # Use the current Python interpreter to run Alembic module to avoid PATH issues
    return subprocess.call([sys.executable, "-m", "alembic", *alembic_args], env=env)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_all_shards.py <alembic-args>")
        print("Example: python scripts/migrate_all_shards.py upgrade head")
        sys.exit(1)

    alembic_args = sys.argv[1:]

    shard_urls = SHARD_DB_URL_LIST or []
    if not shard_urls:
        print("No SHARD_DB_URLS configured. Exiting.")
        sys.exit(1)

    exit_code = 0
    for url in shard_urls:
        code = run_for_shard(url, alembic_args)
        if code != 0:
            exit_code = code
            print(f"Alembic command failed for shard: {url} with exit code {code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
