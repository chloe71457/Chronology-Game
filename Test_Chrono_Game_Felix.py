#!/usr/bin/env python3
"""
Chronology (Hitster-style) console game.

Modes:
  1) Single Player
  2) Two Players
Pool:
  a) Standard (all songs)
  b) Popular only (track_popularity >= 75)

Type "EXIT" at any placement prompt to return to main menu.
Shows clickable (or plain) links for each challenge song.
"""

from __future__ import annotations
import argparse
import streamlit as st
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from pathlib import Path
import pandas as pd




# ------ FrontEnd -----------------------


# -------------------------------------------------
# App config & paths
# -------------------------------------------------
st.set_page_config(page_title="HitStory", page_icon="🎵", layout="wide")
APP_DIR = Path(__file__).parent
LOGO = APP_DIR / "Logo_V1.png"

# Brand colors
PURPLE = "#2D0D57"
PANEL = "#4978C8"
PANEL_BORDER = "#2a4d98"
PINK = "#ff5aa3"
TEXT = "#ffffff"

# -------------------------------------------------
# Global CSS (including timeline styling)
# -------------------------------------------------
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

    .stButton>button {{
      background: linear-gradient(180deg,#ff77b4,#ff5aa3);
      color: white;
      font-weight: 800;
      border: none;
      border-radius: 12px;
      box-shadow: 0 5px 0 #c23c79;
      padding: .8rem 1rem;
    }}
    .stButton>button:hover {{ filter: brightness(1.05); }}
    .stButton>button:active {{
      transform: translateY(2px);
      box-shadow: 0 3px 0 #c23c79;
    }}

    .rowgap {{ margin: .4rem 0 .6rem 0; }}
    .hint {{ opacity:.9; font-weight:600; }}

    /* Timeline layout */
    .timeline-wrapper {{
      position: relative;
      margin-top: 2.5rem;
    }}
    .timeline-line {{
      position: absolute;
      left: 5%;
      right: 5%;
      top: 50%;
      height: 4px;
      background: var(--pink);
      z-index: 0;
    }}
    .timeline {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.5rem;
      position: relative;
      z-index: 1;
    }}
    .timeline-item {{
      flex: 1;
      text-align: center;
      font-size: 0.8rem;
    }}
    .timeline-cover {{
      width: 90px;
      height: 90px;
      margin: 0 auto 0.6rem auto;
      border-radius: 4px;
      background: var(--pink);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      line-height: 1.1;
      overflow: hidden;
    }}
    .timeline-cover img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .timeline-dot {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #e4e4e4;
      border: 4px solid var(--pink);
      margin: 0.3rem auto 0.15rem auto;
    }}
    .timeline-year {{
      margin-top: 0.1rem;
      font-weight: 600;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Navigation state
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"  # "home", "single_setup", "single_game", "multi_setup"


def go(page: str):
    """Simple page switcher."""
    st.session_state.page = page


# -------------------------------------------------
# Data model & loading
# -------------------------------------------------
DEFAULT_DATA_PATH = "songs_input.xlsx"
REQUIRED_COLS = ["track_id", "track_name", "track_artist", "year", "track_url"]
OPTIONAL_COLS = ["track_popularity", "track_cover"]


@dataclass(frozen=True)
class Song:
    track_id: int | str
    track_name: str
    track_artist: str
    year: int
    track_url: Optional[str] = None
    popularity: Optional[int] = None
    track_cover: Optional[str] = None

    def label(self, show_year: bool = False) -> str:
        base = f"{self.track_name} — {self.track_artist}"
        return f"{base} ({self.year})" if show_year else base


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


# -------------------------------------------------
# Common header
# -------------------------------------------------
def header_logo():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    if LOGO.exists():
        # use_container_width=True is correct for modern Streamlit
        st.image(LOGO.read_bytes(), use_container_width=False)
    else:
        st.markdown(
            '<h1 style="font-weight:900;color:#fff;">HitStory</h1>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------------------------
# Pages
# -------------------------------------------------
def page_home():
    header_logo()
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("Singleplayer", use_container_width=True):
            go("single_setup")
        st.write("")
        if st.button("Multiplayer", use_container_width=True):
            go("multi_setup")


def page_single_setup():
    if "single" not in st.session_state:
        st.session_state.single = {"mode": "Standard", "lives": 3}

    header_logo()
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
              <li>Place the song correctly on the timeline according to its release year.</li>
              <li>If you lose all lives, play again!</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        # Game mode
        st.markdown('<div class="panel">Select Game-mode</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1:
            if st.button("🎵  Standard", use_container_width=True, key="s_std"):
                st.session_state.single["mode"] = "Standard"
        with g2:
            if st.button("⭐  Popular", use_container_width=True, key="s_pop"):
                st.session_state.single["mode"] = "Popular"
        with g3:
            if st.button("🥳  Party", use_container_width=True, key="s_party"):
                st.session_state.single["mode"] = "Party"

        # Lives
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">Select Lives</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        l1, l2, l3 = st.columns(3)
        with l1:
            if st.button("③  Standard", use_container_width=True, key="s_l3"):
                st.session_state.single["lives"] = 3
        with l2:
            if st.button("①  Hardcore", use_container_width=True, key="s_l1"):
                st.session_state.single["lives"] = 1
        with l3:
            if st.button("⑤  Fun", use_container_width=True, key="s_l5"):
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
    if st.button("⬅ Back to Home", key="back_single_home"):
        go("home")


def init_single_game_state():
    """Create basic game state: one current song + timeline from dataset."""
    if "songs_all" not in st.session_state:
        try:
            st.session_state.songs_all = load_songs(DEFAULT_DATA_PATH)
        except Exception as e:
            st.error(f"Error loading songs: {e}")
            st.stop()

    all_songs = st.session_state.songs_all
    single_cfg = st.session_state.get("single", {"mode": "Standard", "lives": 3})
    pool = build_pool(all_songs, single_cfg.get("mode", "Standard"))
    if not pool:
        st.error("No songs available in the selected pool.")
        st.stop()

    current = random.choice(pool)
    timeline_candidates = [s for s in pool if s.track_id != current.track_id]
    k = min(8, len(timeline_candidates))
    timeline = sorted(random.sample(timeline_candidates, k=k), key=lambda s: s.year) if k > 0 else []

    st.session_state.single_game = {
        "pool": pool,
        "timeline": timeline,
        "current": current,
        "lives_max": single_cfg.get("lives", 3),
        "lives": single_cfg.get("lives", 3),
        "score": 0,
    }


def render_timeline_ui(timeline: List[Song]):
    if not timeline:
        st.caption("Timeline will appear here.")
        return

    html_parts = [
        '<div class="timeline-wrapper">',
        '<div class="timeline-line"></div>',
        '<div class="timeline">',
    ]

    for song in timeline:
        if song.track_cover:
            cover_html = f'<img src="{song.track_cover}" alt="cover" />'
        else:
            cover_html = "Album<br/>Cover"

        html_parts.append(
            f"""
          <div class="timeline-item">
            <div class="timeline-cover">{cover_html}</div>
            <div class="timeline-dot"></div>
            <div class="timeline-year">{song.year}</div>
          </div>
        """
        )

    html_parts.append("</div></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def page_single_game():
    if "single_game" not in st.session_state:
        init_single_game_state()

    game = st.session_state.single_game
    current: Song = game["current"]
    timeline: List[Song] = game["timeline"]

    header_logo()

    # Scoreboard (top left)
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

    # Center: album cover + title bar
    center = st.columns([1, 2, 1])[1]
    with center:
        if current.track_cover:
            st.image(current.track_cover, use_container_width=True)
        else:
            st.markdown(
                """
                <div style="
                  width:100%;
                  padding-top:100%;
                  border-radius:12px;
                  background:linear-gradient(135deg,#ff77b4,#4978C8);
                  display:flex;
                  align-items:center;
                  justify-content:center;
                  font-size:2.5rem;
                  font-weight:900;
                  margin-bottom:1rem;
                ">
                  🎵
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="panel" style="margin-top:1rem;">
              {current.track_name} — {current.track_artist}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current.track_url:
            st.audio(current.track_url)

    # Bottom: timeline
    render_timeline_ui(timeline)

    st.write("")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Back to setup", key="back_single_setup"):
            go("single_setup")
    with col_next:
        if st.button("Next random song ➜"):
            init_single_game_state()


def page_multi_setup():
    if "multi" not in st.session_state:
        st.session_state.multi = {"players": 2, "names": [], "mode": "Standard", "lives": 3}

    header_logo()
    st.markdown('<div class="panel">👥 Multiplayer!</div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1.3], gap="large")

    with left:
        st.markdown('<div class="panel soft">', unsafe_allow_html=True)
        st.markdown("### How to play!", unsafe_allow_html=True)
        st.markdown(
            """
            <ul class="how">
              <li>How many players? Enter all of the names.</li>
              <li>Choose your game-mode & how many lives you want.</li>
              <li>Listen to the song that is being played.</li>
              <li>A hint will be given if needed (artist & song name).</li>
              <li>Place the song correctly on the timeline according to its release year.</li>
              <li>If you lose all lives, play again!</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">Select number of players (2–5)</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.session_state.multi["players"] = st.slider(
            "", min_value=2, max_value=5, value=st.session_state.multi["players"], key="m_count"
        )

        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">Input Names</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        names = []
        cols = st.columns(2)
        for i in range(st.session_state.multi["players"]):
            col = cols[i % 2]
            with col:
                default = st.session_state.multi["names"][i] if i < len(st.session_state.multi["names"]) else ""
                names.append(st.text_input(f"Player {i+1}", value=default, key=f"m_name_{i}"))
        st.session_state.multi["names"] = names

        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">Select Game-mode</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1:
            if st.button("🎵  Standard", use_container_width=True, key="m_std"):
                st.session_state.multi["mode"] = "Standard"
        with g2:
            if st.button("⭐  Popular", use_container_width=True, key="m_pop"):
                st.session_state.multi["mode"] = "Popular"
        with g3:
            if st.button("🥳  Party", use_container_width=True, key="m_party"):
                st.session_state.multi["mode"] = "Party"

        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel">Select Lives</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        l1, l2, l3 = st.columns(3)
        with l1:
            if st.button("③  Standard", use_container_width=True, key="m_l3"):
                st.session_state.multi["lives"] = 3
        with l2:
            if st.button("①  Hardcore", use_container_width=True, key="m_l1"):
                st.session_state.multi["lives"] = 1
        with l3:
            if st.button("⑤  Fun", use_container_width=True, key="m_l5"):
                st.session_state.multi["lives"] = 5

        st.caption(
            f"""<div class="hint">Selected: <b>{st.session_state.multi['mode']}</b> • <b>{st.session_state.multi['lives']}</b> lives • Players: <b>{st.session_state.multi['players']}</b></div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        mid = st.columns([1, 1, 1])[1]
        with mid:
            if st.button("Continue ➜", use_container_width=True, type="primary", key="m_next"):
                st.info("Multiplayer gameplay page not implemented yet 🙂")

    st.write("")
    if st.button("⬅ Back to Home", key="back_multi_home"):
        go("home")


# -------------------------------------------------
# Router
# -------------------------------------------------
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


# ---------------- Config ----------------
DEFAULT_DATA_PATH = "songs_input.xlsx"
REQUIRED_COLS = ["track_id", "track_name", "track_artist", "year", "track_url"]
OPTIONAL_COLS = ["track_popularity", "track_cover"]

# ---------------- Data model ----------------
@dataclass(frozen=True)
class Song:
    track_id: int | str
    track_name: str
    track_artist: str
    year: int
    track_url: str | None = None
    popularity: Optional[int] = None
    track_cover: Optional[str] = None

    def label(self, show_year: bool = False) -> str:
        base = f"{self.track_name} — {self.track_artist}"
        return f"{base} ({self.year})" if show_year else base

# ---------------- Loading ----------------
def load_songs(path: str) -> List[Song]:
    if path.lower().endswith(".xlsx"):
        df = pd.read_excel(path)
    elif path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        raise SystemExit("Unsupported file type. Use .xlsx or .csv")

    df.columns = [c.lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"Dataset missing columns: {missing}. Required: {REQUIRED_COLS}")

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
                track_url=None if "track_url" not in df.columns or pd.isna(getattr(row, "track_url", None))
                else str(getattr(row, "track_url")),
                popularity=None if "track_popularity" not in df.columns
                                  or pd.isna(getattr(row, "track_popularity", None))
                else int(getattr(row, "track_popularity")),
                track_cover=None if "track_cover" not in df.columns or pd.isna(getattr(row, "track_cover", None))
                else str(getattr(row, "track_cover")),
            )
        )
    if not songs:
        raise SystemExit("No valid songs found.")
    return songs


def filter_popular(songs: List[Song], threshold: int = 75) -> List[Song]:
    """Return only songs with track_popularity >= threshold (if present)."""
    return [s for s in songs if s.popularity is not None and s.popularity >= threshold]

# ---------------- Game mechanics ----------------
def choose_next_song(pool: List[Song], used_ids: Set, used_years: Set[int]) -> Optional[Song]:
    candidates = [s for s in pool if s.track_id not in used_ids and s.year not in used_years]
    return random.choice(candidates) if candidates else None


def is_correct_insertion(timeline: List[Song], new_song: Song, insert_idx: int) -> bool:
    tl_sorted = sorted(timeline, key=lambda s: s.year)
    tentative = tl_sorted[:insert_idx] + [new_song] + tl_sorted[insert_idx:]
    years = [s.year for s in tentative]
    return years == sorted(years) and len(years) == len(set(years))


def render_timeline(timeline: List[Song]) -> None:
    print("-" * 64)
    print("🕓 Current timeline:")
    for i, s in enumerate(sorted(timeline, key=lambda x: x.year), start=1):
        print(f"  {i}. {s.label(show_year=True)}")
    print("-" * 64 + "\n")

# ---------------- Link helpers ----------------
def supports_ansi_hyperlinks() -> bool:
    term = os.environ.get("TERM", "")
    if sys.platform == "win32":
        return any(k in os.environ for k in ("WT_SESSION", "WindowsTerminal", "VSCODE_PID"))
    return any(k in term for k in ("xterm", "screen", "tmux", "kitty"))


def hyperlink(url: str, text: str) -> str:
    """Clickable link if supported, else full raw URL (works everywhere)."""
    if supports_ansi_hyperlinks():
        return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
    return f"{text}: {url}"


def show_link_for_challenge(song: Song):
    if song.track_url:
        print(f"   🎧 {hyperlink(song.track_url, 'Listen here')}\n")
    else:
        print("   (No preview available)\n")

# ---------------- Prompt / options ----------------
def ask_position(timeline: List[Song], challenge: Song) -> Optional[int]:
    tl = sorted(timeline, key=lambda x: x.year)
    print(f"🎶 Place this song:  \033[1m{challenge.label(False)}\033[0m\n")
    show_link_for_challenge(challenge)
    print("Choose where this song's year fits (or type 'EXIT' to go back):\n")

    allowed_positions: List[int] = [0]
    for i in range(len(tl) - 1):
        if tl[i + 1].year - tl[i].year > 1:
            allowed_positions.append(i + 1)
    allowed_positions.append(len(tl))

    tokens: List[str] = []
    opt_num = 1
    tokens.append(f"Option {opt_num}")
    for i, s in enumerate(tl):
        tokens += ["<", f"\033[1m({s.year})\033[0m"]
        if i < len(tl) - 1 and (tl[i + 1].year - s.year > 1):
            opt_num += 1
            tokens += ["<", f"Option {opt_num}"]
    opt_num += 1
    tokens += ["<", f"Option {opt_num}"]

    print("  " + " ".join(tokens) + "\n")

    while True:
        choice = input(f"Your choice (1..{len(allowed_positions)}, or EXIT): ").strip().lower()
        if choice == "exit":
            return None
        try:
            val = int(choice)
            if 1 <= val <= len(allowed_positions):
                return allowed_positions[val - 1]
        except ValueError:
            pass
        print("Invalid input. Try again.\n")

# ---------------- Helpers ----------------
def hearts(n: int, max_hearts: int) -> str:
    return "❤️" * max(0, n) + "♡" * max(0, (max_hearts - n))


def get_int_in_range(prompt: str, lo: int, hi: int) -> int:
    while True:
        s = input(f"{prompt} ({lo}-{hi}): ").strip()
        try:
            n = int(s)
            if lo <= n <= hi:
                return n
        except ValueError:
            pass
        print(f"Please enter a number between {lo} and {hi}.\n")


def get_player_count() -> int:
    return get_int_in_range("How many players", 1, 4)


def get_player_names(n: int) -> Tuple[str, ...]:
    print(f"\nEnter {n} player name(s) separated by commas (e.g. Alice,Bob,…).")
    raw = input("Names: ").strip()
    names = [p.strip() for p in raw.split(",")] if raw else []
    names = [name if name else f"Player {i+1}" for i, name in enumerate(names[:n])]
    while len(names) < n:
        names.append(f"Player {len(names)+1}")
    return tuple(names)


def next_alive_from(current_idx: int, lives: List[int]) -> Optional[int]:
    if not lives or sum(1 for v in lives if v > 0) == 0:
        return None
    n = len(lives)
    for step in range(1, n + 1):
        j = (current_idx + step) % n
        if lives[j] > 0:
            return j
    return None


def choose_lives_preset() -> int:
    """Return the max lives per player based on preset selection."""
    print("\nSelect Lives:")
    print("  (1) Standard — 3 lives")
    print("  (2) Hardcore — 1 life")
    print("  (3) Fun — 5 lives")
    while True:
        sel = input("Your choice: ").strip()
        if sel == "1":
            return 3
        if sel == "2":
            return 1
        if sel == "3":
            return 5
        print("Enter 1, 2, or 3.\n")


# ----------- Gamemode selection -----------
def choose_gamemode_single() -> str:
    """Singleplayer game-mode."""
    print("\n🎮 Select Game-mode:")
    print("  (1) Standard  — all songs")
    print("  (2) Popular   — track_popularity ≥ 75")
    while True:
        sel = input("Your choice: ").strip()
        if sel == "1":
            return "Standard"
        if sel == "2":
            return "Popular"
        print("Enter 1 or 2.\n")


def choose_gamemode_multi() -> str:
    """Multiplayer game-mode (adds Party)."""
    print("\n🎮 Select Game-mode:")
    print("  (1) Standard")
    print("  (2) Popular")
    print("  (3) Party  🍻")
    while True:
        sel = input("Your choice: ").strip()
        if sel == "1":
            return "Standard"
        if sel == "2":
            return "Popular"
        if sel == "3":
            return "Party"
        print("Enter 1, 2, or 3.\n")


def build_pool(all_songs: List[Song], mode: str) -> List[Song]:
    """Return appropriate pool for mode. Party always uses Popular."""
    if mode in ("Popular", "Party"):
        popular = filter_popular(all_songs, 75)
        if not popular:
            print("No songs meet ≥75 popularity. Using Standard pool.\n")
            return all_songs
        print(f"\n🎧 Using Popular pool: {len(popular)} songs.\n")
        return popular
    # Standard
    return all_songs


# ---------------- Single-player ----------------
def play_single(all_songs: List[Song], max_lives: int, mode: str) -> bool:
    song_pool = build_pool(all_songs, mode)

    random.seed()
    starter = random.choice(song_pool)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}
    lives, score = max_lives, 0

    print("\n" + "=" * 64)
    print(f"🎵  Chronology — Single Player • Mode: {mode}")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}\n")
    print(f"Lives: {hearts(lives, max_lives)}   Score: {score}\n")

    while True:
        cand = choose_next_song(song_pool, used_ids, used_years)
        if cand is None:
            print("\nNo more valid songs — you cleared the deck! 🎉")
            print(f"Final score: {score}\n")
            return True

        render_timeline(timeline)
        idx = ask_position(timeline, cand)
        if idx is None:
            print("\n↩️ Returning to main menu...\n")
            return False

        if is_correct_insertion(timeline, cand, idx):
            score += 1
            print(f"\033[92m✅ Correct!\033[0m   Year: {cand.year}\n")
            # Singleplayer keeps original behavior: add to timeline on any guess
            timeline = sorted(timeline + [cand], key=lambda s: s.year)
        else:
            lives -= 1
            print(f"\033[91m❌ Wrong!\033[0m   '{cand.track_name}' was {cand.year}")
            print(f"Remaining lives: {hearts(lives, max_lives)}\n")
            # Wrong guess: still add to timeline in singleplayer (unchanged)
            timeline = sorted(timeline + [cand], key=lambda s: s.year)

        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        if lives <= 0:
            print("\n💥 Game over.")
            print(f"Final score: {score}\n")
            return True

# ---------------- Multiplayer (1–4) ----------------
def describe_party_rules():
    print("\n🎉 Party Mode rules active! 🍻")
    print("  1) Incorrect guess → take a sip 🍻")
    print("  2) Streak of 3 correct → pick someone else to sip 🍻")
    print("  3) Off by 3+ songs → chug your drink 🍺\n")


def choose_other_player(pnames: List[str], current: int, lives: List[int]) -> Optional[int]:
    alive_others = [i for i, v in enumerate(lives) if v > 0 and i != current]
    if not alive_others:
        return None
    print("Select a player to take a sip:")
    for k, idx in enumerate(alive_others, start=1):
        print(f"  ({k}) {pnames[idx]}")
    while True:
        sel = input("Your choice: ").strip()
        try:
            k = int(sel)
            if 1 <= k <= len(alive_others):
                return alive_others[k - 1]
        except ValueError:
            pass
        print("Invalid choice.\n")


def play_multi(all_songs: List[Song], player_names: Tuple[str, ...], max_lives: int, mode: str) -> bool:
    song_pool = build_pool(all_songs, mode)

    random.seed()
    starter = random.choice(song_pool)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}

    pnames = list(player_names)
    P = len(pnames)
    lives = [max_lives for _ in range(P)]
    scores = [0 for _ in range(P)]
    streaks = [0 for _ in range(P)]
    sips   = [0 for _ in range(P)]
    chugs  = [0 for _ in range(P)]
    current = 0

    print("\n" + "=" * 64)
    print(f"🎵  Chronology — {P} Player{'s' if P!=1 else ''} • Mode: {mode}")
    print("=" * 64)
    if mode == "Party":
        describe_party_rules()
    print(f"Starter: {starter.label(True)}\n")
    for i in range(P):
        print(f"{pnames[i]}  Lives: {hearts(lives[i], max_lives)}   Score: {scores[i]}")
    print()

    while True:
        if sum(1 for v in lives if v > 0) == 0:
            print("\n💥 All players are out.")
            break

        if lives[current] <= 0:
            nxt = next_alive_from(current, lives)
            if nxt is None:
                print("\n💥 All players are out.")
                break
            current = nxt

        cand = choose_next_song(song_pool, used_ids, used_years)
        if cand is None:
            print("\nNo more songs — you cleared the deck! 🎉")
            break

        render_timeline(timeline)
        print(f"Turn: \033[1m{pnames[current]}\033[0m   Lives: {hearts(lives[current], max_lives)}   Score: {scores[current]}\n")
        idx = ask_position(timeline, cand)
        if idx is None:
            print("\n↩️ Returning to main menu...\n")
            return False

        # Compute the true correct index among all slots (0..len(timeline))
        tl_sorted = sorted(timeline, key=lambda s: s.year)
        true_idx = sum(1 for s in tl_sorted if s.year < cand.year)
        offset_songs = abs(idx - true_idx)

        if is_correct_insertion(timeline, cand, idx):
            scores[current] += 1
            streaks[current] += 1
            print(f"\033[92m✅ Correct, {pnames[current]}!\033[0m   Year: {cand.year} • Streak: {streaks[current]}\n")
            # Multiplayer refinement: only add to timeline when CORRECT
            timeline = sorted(timeline + [cand], key=lambda s: s.year)

            # Party rule 2: streak of 3 -> pick someone to sip
            if mode == "Party" and streaks[current] == 3:
                target = choose_other_player(pnames, current, lives)
                if target is not None:
                    sips[target] += 1  # count the awarded sip
                    print(f"🎉 {pnames[current]} earned a streak of 3! {pnames[current]} selects {pnames[target]} — take a sip 🍻\n")
                streaks[current] = 0  # reset after reward
        else:
            # Wrong answer
            streaks[current] = 0
            lives[current] -= 1
            print(f"\033[91m❌ Wrong, {pnames[current]}!\033[0m   '{cand.track_name}' was {cand.year}")

            # Party rule messages/counters:
            if mode == "Party":
                if offset_songs >= 3:
                    chugs[current] += 1
                    print("😵 Party rule: off by 3+ songs — chug your drink 🍺")
                else:
                    sips[current] += 1
                    print("👉 Party rule: take a sip 🍻")

            print(f"Remaining lives: {hearts(lives[current], max_lives)}\n")

            if lives[current] == 0:
                print(f"🪦 {pnames[current]} has been eliminated!\n")

            # Multiplayer refinement: DO NOT add wrong guess to timeline

        # Regardless of correctness, the song is consumed from the pool
        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        nxt = next_alive_from(current, lives)
        if nxt is None:
            print("\n💥 All players are out.")
            break
        current = nxt

    print("\nFinal scores:")
    for i in range(P):
        print(f"  {pnames[i]} — Score: {scores[i]}   Lives: {hearts(lives[i], max_lives)}")

    # Show Party counters if relevant
    if mode == "Party":
        print("\n🍻 Party tally:")
        for i in range(P):
            print(f"  {pnames[i]} — Sips: {sips[i]}   Chugs: {chugs[i]}")

    max_score = max(scores) if scores else 0
    winners = [pnames[i] for i, sc in enumerate(scores) if sc == max_score]
    if len(winners) == 1:
        print(f"\n🏆 Winner: {winners[0]}!")
    else:
        print("\n🤝 It’s a tie between: " + ", ".join(winners))
    print()
    return True

# ---------------- Main ----------------
def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Hitster-style chronology game (console).")
    parser.add_argument("data", nargs="?", default=DEFAULT_DATA_PATH,
                        help="Path to .xlsx/.csv dataset.")
    args = parser.parse_args(argv)

    try:
        all_songs = load_songs(args.data)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

    while True:
        print("\nSelect game mode:")
        print("  (1) Single Player")
        print("  (2) Multiplayer (1–4 players)")
        print("  (Q) Quit")
        mode = input("Your choice: ").strip().lower()

        if mode == "q":
            break
        elif mode == "1":
            max_lives = choose_lives_preset()
            gm = choose_gamemode_single()     # Standard / Popular
            play_single(all_songs, max_lives, gm)
        elif mode == "2":
            count = get_player_count()
            pnames = get_player_names(count)
            gm = choose_gamemode_multi()      # Standard / Popular / Party
            max_lives = choose_lives_preset()
            play_multi(all_songs, pnames, max_lives, gm)
        else:
            print("Invalid choice, try again.\n")

    print("\n👋 Thanks for playing!")
    sys.exit(0)

if __name__ == "__main__":
    main()