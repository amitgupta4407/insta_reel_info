"""CLI: Print a clean human-readable summary for an Instagram reel."""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from logger import AppLogger
from reel_core import download_reel, extract_shortcode, find_existing, get_video_path

log = AppLogger("analyze_reel")

PROJECT_ROOT = Path(__file__).parent.resolve()


def summarize(meta: dict, output_dir: Path, cached: bool = False) -> None:
    sc = meta["shortcode"]
    video = get_video_path(sc, output_dir)

    print("=" * 56)
    print(f"  Instagram Reel — {sc}")
    print("=" * 56)
    print(f"  Owner:        @{meta.get('owner_username', '?')}")
    if meta.get("owner_display_name"):
        print(f"  Name:         {meta['owner_display_name']}")
    print(f"  Likes:        {meta.get('likes', 0):,}")
    print(f"  Comments:     {meta.get('comments', 0):,}")
    dur = meta.get("duration")
    print(f"  Duration:     {str(dur) + 's' if dur else '?'}")
    print(f"  Date:         {meta.get('date', '?')}")
    print(f"  URL:          {meta.get('url', '')}")
    if video:
        print(f"  Video:        {video}")
    print(f"  Source:       {'cached' if cached else 'fresh download'}")
    print()

    caption = meta.get("caption", "")
    if caption:
        lines = caption.strip().split("\n")
        print("  Caption:")
        for line in lines:
            print(f"    {line}")
        print()

    hashtags = meta.get("hashtags")
    if hashtags:
        print(f"  Hashtags:     {'  '.join(hashtags)}")
        print()

    top_comments = meta.get("top_comments")
    if top_comments:
        print(f"  Top Comments ({len(top_comments)}):")
        for i, c in enumerate(top_comments, 1):
            text = c.get("text", "")
            likes = c.get("likes", 0)
            author = c.get("author", "?")
            # Truncate long comments for the summary
            if len(text) > 100:
                text = text[:97] + "..."
            print(f"    {i}. @{author} ({likes} ❤️)  {text}")
        print()

    transcript = meta.get("transcript")
    if transcript:
        words = transcript.split()
        preview = " ".join(words[:30])
        if len(words) > 30:
            preview += "..."
        print(f"  Transcript ({len(words)} words):")
        print(f"    {preview}")
        print()

    print("=" * 56)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze an Instagram reel — print a readable summary"
    )
    parser.add_argument("shortcode", help="Reel shortcode or URL")
    parser.add_argument("--dir", default="downloads", help="Output directory")
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        help="Browser to extract cookies from",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config JSON",
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

    cached_data = find_existing(shortcode, output_dir) if not args.force else None

    if cached_data:
        log.info(f"Using cached: {shortcode}")
        summarize(cached_data, output_dir, cached=True)
    else:
        log.info(f"Analyzing reel: {shortcode}")
        meta = download_reel(
            shortcode,
            output_dir,
            cookies_from_browser=args.cookies_from_browser,
            config_path=config_path,
        )
        summarize(meta, output_dir, cached=False)


if __name__ == "__main__":
    main()
