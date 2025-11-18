#!/usr/bin/env python3
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
import streamlit as st

# ---------------- App config ----------------
st.set_page_config(page_title="HitStory", page_icon="🎵", layout="wide")
APP_DIR = Path(__file__).parent
LOGO = APP_DIR / "Logo_V1.png"

# ---------------- Theme colors ----------------
PURPLE = "#2D0D57"
PANEL = "#4978C8"
PANEL_BORDER = "#2a4d98"
PINK = "#ff5aa3"
TEXT = "#ffffff"

# ---------------- Global CSS ----------------
st.markdown(
    f"""
    <style>
    :root {{
      --purple:{PURPLE}; --panel:{PANEL}; --panelBorder:{PANEL_BORDER}; --pink:{PINK}; --text:{TEXT};
    }}

    [data-testid="stAppViewContainer"] {{
      background: var(--purple);
      color: var(--text);
    }}
    [data-testid="stAppViewContainer"] > .main {{
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {{
      display:none !important;
    }}

    .hero {{ text-align:center; margin: 0 0 .5rem 0; }}
    .hero img {{
      max-width: 320px;
      width: 48%;
      margin: 0 auto;
      display: block;
    }}

    .panel {{
      background: var(--panel);
      border: 3px solid var(--panelBorder);
      border-radius: 12px;
      padding: 12px 16px;
      color: white;
      font-weight: 700;
      text-align: center;
    }}
    .panel.soft {{
      text-align: left;
      font-weight: 500;
      line-height: 1.55;
    }}

    .how li::marker {{ color: var(--pink); }}
    .how li {{ margin: .35rem 0; }}

    /* --- BUTTON STYLES --- */

    /* Primary buttons: all normal UI controls (pink rounded) */
    button[data-testid="baseButton-primary"] {{
      background: linear-gradient(180deg,#ff77b4,#ff5aa3);
      color: white;
      font-weight: 800;
      border: none;
      border-radius: 12px;
      box-shadow: 0 5px 0 #c23c79;
      padding: .8rem 1rem;
    }}
    button[data-testid="baseButton-primary"]:hover {{
      filter: brightness(1.05);
    }}
    button[data-testid="baseButton-primary"]:active {{
      transform: translateY(2px);
      box-shadow: 0 3px 0 #c23c79;
    }}

    /* Secondary buttons: ONLY used for timeline circles (grey) */
    button[data-testid="baseButton-secondary"] {{
      border-radius: 50% !important;
      width: 40px !important;
      height: 40px !important;
      padding: 0 !important;
      background: #d9d9d9 !important;        /* grey */
      border: 3px solid #a0a0a0 !important;  /* darker grey ring */
      box-shadow: none !important;
    }}
    button[data-testid="baseButton-secondary"]:hover {{
      filter: brightness(1.08);
    }}

    /* Simple highlight for selected circle */
    .timeline-circle-selected {{
      padding: 2px;
      border-radius: 999px;
      background: rgba(255,182,216,0.45);
      display: inline-block;
    }}

    .rowgap {{ margin: .4rem 0 .6rem 0; }}
    .hint {{ opacity:.9; font-weight:600; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Navigation state ----------------
if "page" not in st.session_state:
    st.session_state.page = "home"   # "home", "single_setup", "single_game", "multi_setup"

def go(page: str) -> None:
    st.session_state.page = page

# ---------------- Data model & loading ----------------
DEFAULT_DATA_PATH = "songs_input.xlsx"
REQUIRED_COLS = ["track_id", "track_name", "track_artist", "year", "track_url"]
OPTIONAL_COLS = ["track_popularity", "track_cover"]

@dataclass(frozen=True)
class Song:
    track_id: Union[int, str]
    track_name: str
    track_artist: str
    year: int
    track_url: Optional[str] = None
    popularity: Optional[int] = None
    track_cover: Optional[str] = None

def load_songs(path: str) -> List[Song]:
    if path.lower().endswith(".xlsx"):
        df = pd.read_excel(path)
    elif path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        raise RuntimeError("Unsupported file type. Use .xlsx or .csv")

    df.columns = [c.lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise RuntimeError(f"Dataset missing columns: {missing}. Required: {REQUIRED_COLS}")

    keep_cols = REQUIRED_COLS + [c for c in OPTIONAL_COLS if c in df.columns]
    df = df[keep_cols].copy()

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "track_popularity" in df.columns:
        df["track_popularity"] = pd.to_numeric(df["track_popularity"], errors="coerce").astype("Int64")

    df = df.dropna(subset=["track_name", "track_artist", "year"])
    df["year"] = df["year"].astype(int)
    df = df.drop_duplicates(subset=["track_id", "year"]).reset_index(drop=True)

    songs: List[Song] = []
    for row in df.itertuples(index=False):
        songs.append(
            Song(
                track_id=getattr(row, "track_id"),
                track_name=getattr(row, "track_name"),
                track_artist=getattr(row, "track_artist"),
                year=int(getattr(row, "year")),
                track_url=None
                if "track_url" not in df.columns or pd.isna(getattr(row, "track_url", None))
                else str(getattr(row, "track_url")),
                popularity=None
                if "track_popularity" not in df.columns
                or pd.isna(getattr(row, "track_popularity", None))
                else int(getattr(row, "track_popularity")),
                track_cover=None
                if "track_cover" not in df.columns or pd.isna(getattr(row, "track_cover", None))
                else str(getattr(row, "track_cover")),
            )
        )
    if not songs:
        raise RuntimeError("No valid songs found.")
    return songs

def filter_popular(songs: List[Song], threshold: int = 75) -> List[Song]:
    return [s for s in songs if s.popularity is not None and s.popularity >= threshold]

def build_pool(all_songs: List[Song], mode: str) -> List[Song]:
    if mode in ("Popular", "Party"):
        popular = filter_popular(all_songs, 75)
        return popular if popular else all_songs
    return all_songs

def hearts(n: int, max_hearts: int) -> str:
    return "❤️" * max(0, n) + "♡" * max(0, (max_hearts - n))

# ---------------- Common header ----------------
def header_logo():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    if LOGO.exists():
        st.image(LOGO.read_bytes(), use_container_width=False)
    else:
        st.markdown('<h1 style="font-weight:900;color:#fff;">HitStory</h1>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Pages ----------------
def page_home():
    header_logo()
    st.write(f"DEBUG – current page: {st.session_state.page}")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("Singleplayer", use_container_width=True, type="primary"):
            go("single_setup")
        st.write("")
        if st.button("Multiplayer", use_container_width=True, type="primary"):
            go("multi_setup")

def page_single_setup():
    if "single" not in st.session_state:
        st.session_state.single = {"mode": "Standard", "lives": 3}

    header_logo()
    st.write(f"DEBUG – current page: {st.session_state.page}")
    st.markdown('<div class="panel">🧍 Singleplayer!</div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1.3], gap="large")

    with left:
        st.markdown('<div class="panel soft">', unsafe_allow_html=True)
        st.markdown("### How to play!", unsafe_allow_html=True)
        st.markdown(
            """
            <ul class="how">
              <li>Choose your game-mode & how many lives you want.</li>
              <li>Listen to the song that is being played.</li>
              <li>A hint will be given if needed (artist & song name).</li>
              <li>Click a circle on the timeline to place the song in the correct year.</li>
              <li>If you lose all lives, play again!</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">Select Game-mode</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1:
            if st.button("🎵  Standard", use_container_width=True, key="s_std", type="primary"):
                st.session_state.single["mode"] = "Standard"
        with g2:
            if st.button("⭐  Popular", use_container_width=True, key="s_pop", type="primary"):
                st.session_state.single["mode"] = "Popular"
        with g3:
            if st.button("🥳  Party", use_container_width=True, key="s_party", type="primary"):
                st.session_state.single["mode"] = "Party"

        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">Select Lives</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        l1, l2, l3 = st.columns(3)
        with l1:
            if st.button("③  Standard", use_container_width=True, key="s_l3", type="primary"):
                st.session_state.single["lives"] = 3
        with l2:
            if st.button("①  Hardcore", use_container_width=True, key="s_l1", type="primary"):
                st.session_state.single["lives"] = 1
        with l3:
            if st.button("⑤  Fun", use_container_width=True, key="s_l5", type="primary"):
                st.session_state.single["lives"] = 5

        st.caption(
            f"""<div class="hint">Selected: <b>{st.session_state.single['mode']}</b> • <b>{st.session_state.single['lives']}</b> lives</div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        mid = st.columns([1, 1, 1])[1]
        with mid:
            if st.button("Continue ➜", use_container_width=True, type="primary", key="s_next"):
                go("single_game")

    st.write("")
    if st.button("⬅ Back to Home", key="back_single_home", type="primary"):
        go("home")

# ---------- single game helpers ----------
def init_single_game_state():
    if "songs_all" not in st.session_state:
        st.session_state.songs_all = load_songs(DEFAULT_DATA_PATH)

    all_songs = st.session_state.songs_all
    cfg = st.session_state.get("single", {"mode": "Standard", "lives": 3})
    pool = build_pool(all_songs, cfg.get("mode", "Standard"))
    if not pool:
        st.error("No songs available in the selected pool.")
        st.stop()

    starter = random.choice(pool)
    remaining = [s for s in pool if s.track_id != starter.track_id]
    current = random.choice(remaining)

    st.session_state.single_game = {
        "pool": pool,
        "timeline": [starter],
        "current": current,
        "used_ids": {starter.track_id, current.track_id},
        "lives_max": cfg.get("lives", 3),
        "lives": cfg.get("lives", 3),
        "score": 0,
        "last_feedback": "",
    }
    st.session_state.selected_pos = None

def choose_next_challenge():
    game = st.session_state.single_game
    pool = game["pool"]
    used_ids = game["used_ids"]
    candidates = [s for s in pool if s.track_id not in used_ids]
    if not candidates:
        game["current"] = None
        game["last_feedback"] = "🎉 Deck cleared – no more songs!"
        return
    nxt = random.choice(candidates)
    used_ids.add(nxt.track_id)
    game["current"] = nxt

# ---------- timeline rendering ----------
def render_timeline_ui(timeline: List[Song]):
    """
    Show covers in a row, then a timeline row with pattern:
    button – year – button – year – ... – button
    """
    n = len(timeline)
    if n == 0:
        st.caption("Timeline will appear here.")
        return

    # There are n songs and n+1 possible positions.
    # We create 2*n + 1 columns: even indices = positions, odd = songs.
    num_cols = 2 * n + 1
    cols = st.columns(num_cols)

    # ---- Row 1: covers (only in odd columns) ----
    for idx, col in enumerate(cols):
        if idx % 2 == 1:  # song column
            song_idx = idx // 2
            song = timeline[song_idx]
            with col:
                if song.track_cover:
                    st.image(song.track_cover, use_container_width=True)
                else:
                    st.markdown(
                        """
                        <div style="
                          width:100%;
                          aspect-ratio:1/1;
                          border-radius:12px;
                          background:linear-gradient(135deg,#ff77b4,#4978C8);
                          display:flex;
                          align-items:center;
                          justify-content:center;
                          font-weight:700;
                        ">
                          Album<br/>Cover
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ---- Row 2: timeline row (buttons + years all on same level) ----
    selected = st.session_state.get("selected_pos")

    for idx, col in enumerate(cols):
        with col:
            if idx % 2 == 0:
                # Position column: grey circle
                pos_idx = idx // 2
                highlight_cls = "timeline-circle-selected" if selected == pos_idx else ""
                st.markdown(f'<div style="text-align:center;"><span class="{highlight_cls}">', unsafe_allow_html=True)
                if st.button(" ", key=f"pos_{pos_idx}", type="secondary"):
                    st.session_state.selected_pos = pos_idx
                st.markdown("</span></div>", unsafe_allow_html=True)
            else:
                # Song column: year label
                song_idx = idx // 2
                year = timeline[song_idx].year
                st.markdown(
                    f'<div style="text-align:center;margin-top:0.4rem;font-weight:600;">{year}</div>',
                    unsafe_allow_html=True,
                )

def page_single_game():
    if "single_game" not in st.session_state:
        init_single_game_state()

    game = st.session_state.single_game
    current: Optional[Song] = game["current"]
    timeline: List[Song] = game["timeline"]

    header_logo()
    st.write(f"DEBUG – current page: {st.session_state.page}")

    # Scoreboard
    sb_col, _ = st.columns([1.5, 3])
    with sb_col:
        lives_str = hearts(game["lives"], game["lives_max"])
        st.markdown(
            f"""
            <div class="panel" style="text-align:left;">
              <div style="font-size:1.4rem; line-height:1.2;">Scoreboard</div>
              <div style="margin-top:.5rem;">Player 1 — {lives_str}</div>
              <div>Score — <b>{game['score']}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    center = st.columns([1, 2, 1])[1]
    with center:
        if current is None:
            st.markdown('<div class="panel">No more songs – you cleared the deck! 🎉</div>', unsafe_allow_html=True)
        else:
            if current.track_cover:
                st.markdown(
                    '<div style="display:flex;justify-content:center;margin-bottom:1rem;">',
                    unsafe_allow_html=True,
                )
                st.image(current.track_cover, width=260)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div style="
                      width:260px;
                      height:260px;
                      border-radius:12px;
                      background:linear-gradient(135deg,#ff77b4,#4978C8);
                      display:flex;
                      align-items:center;
                      justify-content:center;
                      font-size:2.5rem;
                      font-weight:900;
                      margin:0 auto 1rem auto;
                    ">
                      🎵
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""
                <div class="panel" style="margin-top:0.5rem;">
                  {current.track_name} — {current.track_artist}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if current.track_url:
                st.audio(current.track_url)

    # Timeline row (covers + Button-Year-Button-... alignment)
    render_timeline_ui(timeline)

    # Feedback
    if game.get("last_feedback"):
        if game["last_feedback"].startswith("✅") or "cleared the deck" in game["last_feedback"]:
            st.success(game["last_feedback"])
        else:
            st.error(game["last_feedback"])

    # Placement confirmation
    if current is not None and game["lives"] > 0:
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.caption("Click a grey circle to choose a position, then confirm:")

        selected_idx = st.session_state.get("selected_pos")

        if st.button("Confirm placement ✅", type="primary"):
            if selected_idx is None:
                st.warning("Please click a circle on the timeline first.")
            else:
                tl_sorted = sorted(timeline, key=lambda s: s.year)
                correct_idx = sum(1 for s in tl_sorted if s.year < current.year)

                if selected_idx == correct_idx:
                    game["score"] += 1
                    game["last_feedback"] = f"✅ Correct! “{current.track_name}” was released in {current.year}."
                else:
                    game["lives"] -= 1
                    game["last_feedback"] = (
                        f"❌ Wrong! “{current.track_name}” was released in {current.year}."
                    )

                # always add song in correct chronological position
                tl_sorted.append(current)
                tl_sorted.sort(key=lambda s: s.year)
                game["timeline"] = tl_sorted

                st.session_state.selected_pos = None

                if game["lives"] <= 0:
                    game["current"] = None
                    game["last_feedback"] += " Game over – no lives left."
                else:
                    choose_next_challenge()

    st.write("")
    col_back, col_restart = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Back to setup", key="back_single_setup", type="primary"):
            go("single_setup")
    with col_restart:
        if st.button("Restart singleplayer", type="primary"):
            init_single_game_state()

def page_multi_setup():
    header_logo()
    st.write(f"DEBUG – current page: {st.session_state.page}")
    st.markdown('<div class="panel">👥 Multiplayer!</div>', unsafe_allow_html=True)
    st.write("Multiplayer setup placeholder…")
    if st.button("⬅ Back to Home", key="back_multi_home", type="primary"):
        go("home")

# ---------------- Router ----------------
page = st.session_state.page

if page == "home":
    page_home()
elif page == "single_setup":
    page_single_setup()
elif page == "single_game":
    page_single_game()
elif page == "multi_setup":
    page_multi_setup()
else:
    page_home()