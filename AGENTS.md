# AGENTS.md — insta-reel-info

## Dependencies & setup
- Python 3.14+ (`.python-version`), uses `uv`.
- `uv sync` to install. `uv.lock` is committed.
- `config.yaml` is gitignored. Controls logger settings (`log_folder`, `log_level`, `days_to_keep_archive`). **Crashes on import if missing** — `logger.py` reads it at module level.
- `config.json` is gitignored. Controls `whisper_model` only (defaults to `"tiny"`).

## Entrypoints
| File | Purpose |
|------|---------|
| `reel_core.py` | Library: download, metadata extraction, whisper transcript, cache, thumbnail download |
| `main.py` | CLI — JSON to stdout (used by OpenCode `/analyze_reel`) |
| `analyze_reel.py` | CLI — human-readable summary |
| `app.py` | Streamlit UI — `uv run streamlit run app.py` |
| `logger.py` | Loguru wrapper with file rotation + stderr fallback. **Has import side effects** (reads `config.yaml`, creates log dirs) |

## No test / lint / typecheck / CI
None exist. Don't look for them.

## Design constraints
- **No cookies, no login, no auth.** This app is strictly for public reels only. Do not add features that require Instagram login, stored cookies, or session tokens. The `cookies_from-browser` param in `yt-dlp` exists but should not be surfaced or expanded on.

## Key gotchas
- **Transcript toggle**: `download_reel(..., transcript=True)` (default). When `False`, ffmpeg + whisper are skipped entirely — no audio extraction, no model load.
- **ffmpeg** must be at `ffmpeg/ffmpeg.exe` (project root). Optional — without it, transcript is silently skipped.
- **Caching**: reads `downloads/{shortcode}/{shortcode}.json`. No invalidation — `--force` bypasses.
- **File triples**: each download produces `downloads/{shortcode}/{shortcode}.mp4`, `.json`, and `_thumb.jpg`.
- **Streamlit gallery state**: The gallery checkbox uses `on_change` callback to clear `st.session_state.selected`. Without this, gallery view never renders because `selected` gets set by the sidebar selectbox before the gallery check runs.
- **Loguru import side effects**: importing `logger.py` reads `config.yaml` and configures sinks. It will raise on import if `config.yaml` is missing or malformed.

## Commands
```powershell
uv run python main.py <shortcode>                    # JSON output
uv run python analyze_reel.py <shortcode>             # human-readable
uv run python analyze_reel.py <shortcode> --force     # re-download
uv run streamlit run app.py                           # UI
```
