"""Streamlit UI: Browse history, download new reels, view paired video+metadata."""

import json
from pathlib import Path

import streamlit as st

from reel_core import download_reel, extract_shortcode, get_video_path

DEFAULT_DIR = str((Path(__file__).parent / "downloads").resolve())


def list_downloads(output_dir: Path) -> list[dict]:
    entries = []
    if not output_dir.exists():
        return entries
    for folder in sorted(output_dir.iterdir()):
        if not folder.is_dir():
            continue
        jp = folder / f"{folder.name}.json"
        if not jp.exists():
            continue
        meta = json.loads(jp.read_text(encoding="utf-8"))
        video = get_video_path(folder.name, output_dir)
        entries.append({"shortcode": folder.name, "meta": meta, "video": video})
    return sorted(entries, key=lambda e: e["meta"].get("date", ""), reverse=True)


def main():
    st.set_page_config(page_title="Insta Reel Info", layout="wide")
    st.title("Instagram Reel Downloader")

    output_dir = Path(
        st.sidebar.text_input("Output directory", value=DEFAULT_DIR)
    )

    # Toggles
    show_caption = st.sidebar.checkbox("Show caption", value=True)
    show_comments = st.sidebar.checkbox("Show top comments", value=True)
    show_transcript = st.sidebar.checkbox("Show transcript", value=True)
    show_json = st.sidebar.checkbox("Show JSON", value=True)
    st.sidebar.divider()

    downloads = list_downloads(output_dir)

    # History sidebar
    st.sidebar.subheader(f"Downloads ({len(downloads)})")
    shortcode_map: dict[str, str] = {}
    for entry in downloads:
        m = entry["meta"]
        date_part = (m.get("date") or "")[:10]
        label = f"@{m.get('owner_username', '?')} — {m.get('likes', 0)} ❤️  ({date_part})"
        shortcode = entry["shortcode"]
        shortcode_map[label] = shortcode

    # New reel input
    st.sidebar.divider()
    new_url = st.sidebar.text_input(
        "New reel URL / shortcode", placeholder="DaQGJYTRa2g",
        key="new_url"
    )
    fetch = st.sidebar.button("Download", type="primary", use_container_width=True)

    # Persist selected shortcode across reruns
    if "selected" not in st.session_state:
        st.session_state.selected = None

    if fetch and new_url:
        try:
            sc = extract_shortcode(new_url)
        except ValueError as e:
            st.sidebar.error(str(e))
            sc = None
        if sc:
            with st.spinner("Downloading..."):
                download_reel(sc, output_dir, transcript=show_transcript)
            st.session_state.selected = sc
            st.rerun()

    # Pick from history
    if downloads and not st.session_state.selected:
        options = list(shortcode_map.keys())
        chosen = st.sidebar.selectbox("Select a reel", options, index=0)
        st.session_state.selected = shortcode_map[chosen]
    elif st.session_state.selected:
        # Show selectbox at current selection
        current = st.session_state.selected
        options = list(shortcode_map.keys())
        rev = {v: k for k, v in shortcode_map.items()}
        idx = options.index(rev.get(current, options[0])) if rev.get(current) in options else 0
        chosen = st.sidebar.selectbox("Select a reel", options, index=idx)
        st.session_state.selected = shortcode_map[chosen]

    selected = st.session_state.selected
    if not selected and downloads:
        selected = downloads[0]["shortcode"]
        st.session_state.selected = selected

    if not selected:
        st.info("No downloads yet. Enter a URL in the sidebar and click Download.")
        return

    # Load selected reel
    jp = output_dir / selected / f"{selected}.json"
    if not jp.exists():
        st.error(f"Metadata not found for {selected}")
        return

    meta = json.loads(jp.read_text(encoding="utf-8"))
    video_path = get_video_path(selected, output_dir)

    # Display
    left, right = st.columns([1, 1])

    with left:
        if video_path and video_path.exists():
            st.subheader("Video")
            st.video(str(video_path))
        elif meta.get("thumbnail"):
            st.image(meta["thumbnail"], use_container_width=True)

        # Files
        folder = output_dir / selected
        st.divider()
        st.subheader("Files")
        for f in sorted(folder.iterdir()):
            size = f.stat().st_size
            unit = "MB" if size > 1024**2 else "KB" if size > 1024 else "B"
            div = 1024**2 if unit == "MB" else 1024 if unit == "KB" else 1
            st.text(f"{f.name}  ({size/div:.1f} {unit})")

    with right:
        st.subheader("Metadata")

        k1, k2, k3 = st.columns(3)
        k1.metric("Likes", meta.get("likes", 0))
        k2.metric("Comments", meta.get("comments", 0))
        k3.metric("Duration", f'{meta.get("duration", "?")}s')

        st.markdown(f"**Owner:** @{meta.get('owner_username', '?')}")
        if meta.get("owner_display_name"):
            st.markdown(f"**Name:** {meta['owner_display_name']}")
        st.markdown(f"**Date:** {meta.get('date', '?')}")
        st.markdown(f"**URL:** [{meta.get('url', '')}]({meta.get('url', '')})")

        if show_caption:
            with st.expander("Caption", expanded=True):
                st.text(meta.get("caption", ""))

        if meta.get("hashtags"):
            st.markdown("**Hashtags:** " + " ".join(f"`{h}`" for h in meta["hashtags"]))
        if meta.get("mentions"):
            st.markdown("**Mentions:** " + ", ".join(meta["mentions"]))

        if show_comments:
            top_comments = meta.get("top_comments")
            if top_comments:
                with st.expander(f"Top Comments ({len(top_comments)})", expanded=False):
                    for i, c in enumerate(top_comments, 1):
                        st.markdown(f"**{i}.** @{c['author']} — {c.get('likes', 0)} ❤️")
                        st.text(c.get("text", ""))
                        if i < len(top_comments):
                            st.divider()

        if show_transcript:
            transcript = meta.get("transcript")
            if transcript:
                with st.expander("Transcript", expanded=False):
                    st.text(transcript)

        if show_json:
            with st.expander("JSON"):
                st.code(json.dumps(meta, indent=2), language="json")


if __name__ == "__main__":
    main()
