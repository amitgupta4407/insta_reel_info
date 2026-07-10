"""Core logic for fetching and downloading Instagram reels."""

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from yt_dlp import YoutubeDL

from logger import AppLogger

log = AppLogger("reel_core")


PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_FFMPEG = PROJECT_ROOT / "ffmpeg" / "ffmpeg.exe"
DEFAULT_CONFIG = PROJECT_ROOT / "config.json"


def load_config(config_path: Path) -> dict:
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def find_ffmpeg(ffmpeg_path: Path | None = None) -> Path | None:
    target = ffmpeg_path or DEFAULT_FFMPEG
    return target if target.exists() else None


def transcribe_audio(audio_path: Path, model_name: str) -> dict:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    text_parts = []
    seg_list = []
    for s in segments:
        text_parts.append(s.text)
        seg_list.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text,
        })
    return {
        "text": " ".join(text_parts).strip(),
        "segments": seg_list,
    }


def extract_shortcode(url_or_shortcode: str) -> str:
    m = re.match(
        r"https?://(?:www\.)?instagram\.com/(?:reel|p)/([\w-]+)", url_or_shortcode
    )
    if m:
        return m.group(1)
    m = re.fullmatch(r"([\w-]+)", url_or_shortcode)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract shortcode from: {url_or_shortcode}")


def download_reel(
    shortcode: str,
    output_dir: Path,
    quiet: bool = True,
    cookies_from_browser: str | None = None,
    config_path: Path | None = None,
    transcript: bool = True,
) -> dict:
    log.info(f"Downloading reel: {shortcode}")
    start = time.time()
    url = f"https://www.instagram.com/reel/{shortcode}/"
    out_dir = output_dir / shortcode
    out_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts: dict = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": quiet,
        "no_warnings": quiet,
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    caption = (info.get("description") or "").strip()
    ext = info.get("ext", "mp4")

    raw_comments: list[dict] = info.get("comments") or []
    raw_comments.sort(key=lambda c: c.get("like_count", 0), reverse=True)
    top_comments = []
    for c in raw_comments[:5]:
        top_comments.append({
            "author": c.get("author", "?"),
            "text": c.get("text", ""),
            "likes": c.get("like_count", 0),
            "timestamp": c.get("timestamp"),
        })

    meta = {
        "shortcode": info["id"],
        "url": info["webpage_url"],
        "owner_username": info.get("channel"),
        "owner_display_name": info.get("uploader"),
        "owner_id": info.get("uploader_id"),
        "caption": caption,
        "likes": info.get("like_count", 0),
        "comments": info.get("comment_count", 0),
        "top_comments": top_comments,
        "date": datetime.fromtimestamp(
            info.get("timestamp", 0), tz=timezone.utc
        ).isoformat(),
        "hashtags": re.findall(r"#\w+", caption),
        "mentions": re.findall(r"@\w+", caption),
        "duration": info.get("duration") or (info.get("requested_downloads") or [{}])[0].get("duration"),
        "thumbnail": info.get("thumbnail"),
        "filename": f"{shortcode}.{ext}",
    }

    # -- transcript via whisper (skip entirely if not wanted) --
    if transcript:
        cfg = load_config(config_path or DEFAULT_CONFIG)
        whisper_model = cfg.get("whisper_model", "tiny")
        ffmpeg_exe = find_ffmpeg()
        video_file = out_dir / f"{shortcode}.{ext}"

        if ffmpeg_exe and video_file.exists():
            temp_wav = out_dir / f"{shortcode}_audio.wav"
            try:
                log.info(f"Transcribing audio: {shortcode}")
                subprocess.run(
                    [str(ffmpeg_exe), "-y", "-i", str(video_file),
                     "-vn", "-acodec", "pcm_s16le", "-ar", "16000",
                     "-ac", "1", str(temp_wav)],
                    capture_output=True, check=True, timeout=300,
                )
                if temp_wav.exists() and temp_wav.stat().st_size > 1000:
                    result = transcribe_audio(temp_wav, whisper_model)
                    meta["transcript"] = result["text"]
                    meta["transcript_segments"] = result["segments"]
                    log.info(f"Transcription done: {shortcode} ({len(result['text'])} chars)")
            except Exception as exc:
                log.error(f"Transcription failed: {shortcode}: {exc}")
            finally:
                if temp_wav.exists():
                    temp_wav.unlink()
        elif not quiet:
            print("[whisper] ffmpeg not found — transcript skipped", file=sys.stderr)

    json_path = out_dir / f"{shortcode}.json"
    json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    thumb_url = meta.get("thumbnail")
    if thumb_url:
        thumb_path = out_dir / f"{shortcode}_thumb.jpg"
        try:
            import urllib.request
            urllib.request.urlretrieve(thumb_url, str(thumb_path))
            meta["thumbnail_local"] = str(thumb_path)
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            meta["thumbnail_local"] = None

    elapsed = time.time() - start
    log.log_timing(f"download_reel({shortcode})", elapsed)
    return meta


def get_video_path(shortcode: str, output_dir: Path) -> Path | None:
    folder = output_dir / shortcode
    if not folder.exists():
        return None
    for f in folder.iterdir():
        if f.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
            return f
    return None


def get_json_path(shortcode: str, output_dir: Path) -> Path | None:
    p = output_dir / shortcode / f"{shortcode}.json"
    return p if p.exists() else None


def find_existing(shortcode: str, output_dir: Path) -> dict | None:
    jp = get_json_path(shortcode, output_dir)
    if jp:
        return json.loads(jp.read_text(encoding="utf-8"))
    return None
