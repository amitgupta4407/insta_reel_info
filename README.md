# insta-reel-info

Download Instagram reel videos + metadata as paired files. No login required.

```
downloads/{shortcode}/
├── {shortcode}.mp4   # video
└── {shortcode}.json  # metadata (caption, likes, comments, hashtags, transcript)
```

## Features

- **No login** — works on public reels, no Instagram account needed
- **Paired output** — video and JSON share the same filename stem
- **CLI** — one-command download
- **Streamlit UI** — browse history, embedded video player, toggle-able sections
- **Transcript** — optional speech-to-text via `faster-whisper` (CPU, local)
- **OpenCode slash command** — `/analyze_reel <url>` in any chat

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```powershell
git clone <repo-url> D:\projects\insta_reel_info
cd D:\projects\insta_reel_info
uv sync
```

### Optional: ffmpeg

Transcript requires `ffmpeg.exe` at `ffmpeg/ffmpeg.exe` in the project root.
Download from [ffmpeg.org](https://ffmpeg.org/download.html).

## CLI

```powershell
uv run python main.py DaQGJYTRa2g
uv run python main.py https://www.instagram.com/reel/DaQGJYTRa2g/ --dir "D:\reels"
```

## Streamlit UI

```powershell
uv run streamlit run app.py
```

Browse all downloaded reels in the sidebar, watch videos, inspect metadata. Toggle caption, comments, transcript, and JSON sections on/off.

## Transcript toggle

When **Show transcript** is OFF in the UI, audio extraction and whisper transcription are skipped entirely — saves CPU time on downloads.

## OpenCode integration

### Global slash command

Add to `~/.config/opencode/opencode.jsonc` (replace paths with your setup):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "analyze_reel": {
      "description": "Download & analyze an Instagram reel",
      "template": "The user wants to analyze an Instagram reel at URL: $ARGUMENTS\n\nRun this exact command:\n```\n/PATH/TO/insta-reel-info/.venv/bin/python /PATH/TO/insta-reel-info/main.py $ARGUMENTS --dir /PATH/TO/insta-reel-info/downloads\n```\n\nRead the JSON output and present a summary: owner, likes, comments, caption, hashtags, and where the video was saved."
    }
  }
}
```

For Windows, replace `/PATH/TO/` with the full path, e.g. `C:\\Users\\you\\projects\\insta-reel-info`.

Then in any OpenCode chat:

```
/analyze_reel https://www.instagram.com/reel/DaQGJYTRa2g/
```

## Project structure

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `analyze_reel.py` | CLI with clean human-readable summary output |
| `app.py` | Streamlit UI with history browser |
| `reel_core.py` | Core logic: download, extract, transcribe |

## Dependencies

- `yt-dlp` — download + metadata
- `streamlit` — web UI
- `faster-whisper` — optional transcript (CPU)
