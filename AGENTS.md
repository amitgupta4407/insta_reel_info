# AGENTS.md — insta-reel-info

## Dependencies & setup
- Python 3.14+ (`.python-version`), uses `uv`.
- `uv sync` to install. `uv.lock` is committed.
- **Dep mismatch**: `pyproject.toml` lists `openai-whisper`, but code (`reel_core.py:31`) imports `faster_whisper`. Fix if you touch deps.
- `config.json` is gitignored (tracked in initial commit only, subsequent changes ignored). Controls `whisper_model` only.

## Entrypoints
| File | Purpose |
|------|---------|
| `reel_core.py` | Library: download, metadata extraction, whisper transcript, cache |
| `main.py` | CLI — JSON to stdout (used by OpenCode `/analyze_reel`) |
| `analyze_reel.py` | CLI — human-readable summary |
| `app.py` | Streamlit UI — `uv run streamlit run app.py` |

## No test / lint / typecheck / CI
None exist. Don't look for them.

## Key gotchas
- **Transcript toggle**: `download_reel(..., transcript=True)` (default). When `False`, ffmpeg + whisper are skipped entirely — no audio extraction, no model load.
- **ffmpeg** must be at `ffmpeg/ffmpeg.exe` (project root). Optional — without it, transcript is silently skipped.
- **Caching**: reads `downloads/{shortcode}/{shortcode}.json`. No invalidation — `--force` bypasses.
- **No auth** — public reels only.
- **File pairs**: each download produces `downloads/{shortcode}/{shortcode}.mp4` + `.json`.

## Commands
```powershell
uv run python main.py <shortcode>                    # JSON output
uv run python analyze_reel.py <shortcode>             # human-readable
uv run python analyze_reel.py <shortcode> --force     # re-download
uv run streamlit run app.py                           # UI
```
