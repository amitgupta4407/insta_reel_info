"""CLI: Download Instagram reel video + metadata as paired files."""

import argparse
import json
import sys
from pathlib import Path

from logger import AppLogger
from reel_core import download_reel, extract_shortcode, find_existing

log = AppLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download reel video + metadata")
    parser.add_argument("shortcode", help="Reel shortcode or URL")
    parser.add_argument("--dir", default="downloads", help="Output directory")
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        help="Browser to extract cookies from (chrome, firefox, edge, etc.)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config JSON (default: config.json next to main.py)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if cached",
    )
    args = parser.parse_args()

    shortcode = extract_shortcode(args.shortcode)
    output_dir = Path(args.dir)
    config_path = Path(args.config) if args.config else None

    log.info(f"CLI download: {shortcode}")

    cached = find_existing(shortcode, output_dir) if not args.force else None
    if cached:
        meta = cached
        log.info(f"Loaded from cache: {shortcode}")
        print(json.dumps(meta, indent=2))
        print(f"\nLoaded from cache: {output_dir / shortcode}/", file=sys.stderr)
        return

    meta = download_reel(
        shortcode,
        output_dir,
        cookies_from_browser=args.cookies_from_browser,
        config_path=config_path,
    )
    print(json.dumps(meta, indent=2))
    print(f"\nSaved to: {output_dir / shortcode}/", file=sys.stderr)


if __name__ == "__main__":
    main()
