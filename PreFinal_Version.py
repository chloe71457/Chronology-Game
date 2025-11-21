#!/usr/bin/env python3
"""
HitStory – Chronology (Hitster-style) Streamlit game.

Singleplayer + Multiplayer with backend rules from console version.

Need to add:
- Home page
    - Center logo
- Settings
    - Delete logo
    - Change minor settings
- Gameplay
    - Delete logo
    - Resize album cover of current song to be smaller
    - Can buttons be centered
    - Make feedback sentence on response accuracy ("Correct" / "Incorrect") in white
    - Move "New game" button to the top right corner
    - Put name of the new player like "[name]'s turn" above the song title name that is being guessed
    - For party mode, make it say "[rule prompts like "Take a sip" a bigger font and center it.


Extras:
- Timeline capped at 12 songs (no more covers added beyond 12)
- Automatic results pages when game ends
- Tracking of score, longest streak and mistakes
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

import pandas as pd
import streamlit as st

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
# Global CSS
# -------------------------------------------------
st.markdown(
    f"""
    <style>
    :root {{
      --purple:{PURPLE}; --panel:{PANEL}; --panelBorder:{PANEL_BORDER};
      --pink:{PINK}; --text:{TEXT};
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
      padding: .6rem .8rem;
    }}
    .stButton>button:hover {{ filter: brightness(1.05); }}
    .stButton>button:active {{
      transform: translateY(2px);
      box-shadow: 0 3px 0 #c23c79;
    }}

    .rowgap {{ margin: .4rem 0 .6rem 0; }}
    .hint {{ opacity:.9; font-weight:600; }}

    /* Slot look (small white rounded squares) */
    .slot-btn > button {{
      background: #ffffff !important;
      color: transparent !important;
      box-shadow: none !important;
      border-radius: 16px !important;
      padding: 1.4rem .6rem !important;
    }}

    .slot-label {{
      font-size: 0.75rem;
      text-align: center;
      opacity: 0.9;
      margin-top: 0.25rem;
    }}

    /* -------------------------------------- */
    /* NEW: Make feedback text always white   */
    /* -------------------------------------- */
    .stAlert > div {{
        color: white !important;
        font-size: 1.1rem !important;
    }}

    /* -------------------------------------- */
    /* NEW: Party mode sip/chug messages     */
    /* -------------------------------------- */
    .party-msg {{
        color: white !important;
        font-size: 1.25rem !important;
        font-weight: 700;
        margin-top: 0.5rem;
        text-align: left;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
# -------------------------------------------------
# Navigation state
# -------------------------------------------------
if "page" not in st.session_state:
    # home, single_setup, single_game, single_results,
    # multi_setup, multi_game, multi_results
    st.session_state.page = "home"


def go(page: str):
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
                track_url=(
                    None
                    if "track_url" not in df.columns
                       or pd.isna(getattr(row, "track_url", None))
                    else str(getattr(row, "track_url"))
                ),
                popularity=(
                    None
                    if "track_popularity" not in df.columns
                       or pd.isna(getattr(row, "track_popularity", None))
                    else int(getattr(row, "track_popularity"))
                ),
                track_cover=(
                    None
                    if "track_cover" not in df.columns
                       or pd.isna(getattr(row, "track_cover", None))
                    else str(getattr(row, "track_cover"))
                ),
            )
        )
    if not songs:
        raise RuntimeError("No valid songs found.")
    return songs


# -------------------------------------------------
# Backend game mechanics
# -------------------------------------------------
def filter_popular(songs: List[Song], threshold: int = 75) -> List[Song]:
    return [s for s in songs if s.popularity is not None and s.popularity >= threshold]


def build_pool(all_songs: List[Song], mode: str) -> List[Song]:
    if mode in ("Popular", "Party"):
        popular = filter_popular(all_songs, 75)
        return popular if popular else all_songs
    return all_songs


def choose_next_song(pool: List[Song], used_ids: Set, used_years: Set[int]) -> Optional[Song]:
    candidates = [s for s in pool if s.track_id not in used_ids and s.year not in used_years]
    return random.choice(candidates) if candidates else None


def is_correct_insertion(timeline: List[Song], new_song: Song, insert_idx: int) -> bool:
    tl_sorted = sorted(timeline, key=lambda s: s.year)
    tentative = tl_sorted[:insert_idx] + [new_song] + tl_sorted[insert_idx:]
    years = [s.year for s in tentative]
    return years == sorted(years) and len(years) == len(set(years))


def compute_allowed_positions(timeline: List[Song]) -> List[int]:
    """
    Same logic as console:
    - Always allow before first (0) and after last (len)
    - Allow between songs only if there is at least 1 year gap.
    """
    tl = sorted(timeline, key=lambda x: x.year)
    if not tl:
        return [0]

    allowed_positions: List[int] = [0]
    for i in range(len(tl) - 1):
        if tl[i + 1].year - tl[i].year > 1:
            allowed_positions.append(i + 1)
    allowed_positions.append(len(tl))
    return allowed_positions


def hearts(n: int, max_hearts: int) -> str:
    return "❤️" * max(0, n) + "♡" * max(0, (max_hearts - n))


def next_alive_from(current_idx: int, lives: List[int]) -> Optional[int]:
    """Find next player with lives > 0, or None if all dead."""
    if not lives or sum(1 for v in lives if v > 0) == 0:
        return None
    n = len(lives)
    for step in range(1, n + 1):
        j = (current_idx + step) % n
        if lives[j] > 0:
            return j
    return None


# -------------------------------------------------
# Common header
# -------------------------------------------------
def header_logo():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    if LOGO.exists():
        st.image(LOGO.read_bytes(), use_container_width=False)
    else:
        st.markdown(
            '<h1 style="font-weight:900;color:#fff;">HitStory</h1>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------------------------
# Home
# -------------------------------------------------

def header_logo():
    """Display centered logo on the page."""
    st.write("")  # top spacing (optional)
    c1, c2, c3 = st.columns([1, 2, 1])  # wider middle column for the logo
    with c2:
        st.image(LOGO, use_container_width=True)
    st.write("")  # bottom spacing (optional)


def page_home():
    """Home page with centered logo and mode selection buttons."""
    header_logo()

    # Center the buttons under the logo
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("Singleplayer", use_container_width=True):
            go("single_setup")

        st.write("")  # small vertical gap

        if st.button("Multiplayer", use_container_width=True):
            go("multi_setup")


# -------------------------------------------------
# Singleplayer setup & state
# -------------------------------------------------
def page_single_setup():
    if "single" not in st.session_state:
        st.session_state.single = {"mode": "Standard", "lives": 3}

    st.markdown('<div class="panel">🧍 Singleplayer!</div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1.3], gap="large")

    with left:
        st.markdown('<div class="panel soft">', unsafe_allow_html=True)
        st.markdown("### How to play — Singleplayer", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="how">
              <p>Play solo and test your music-timeline skills!</p>
              <ol>
                <li><strong>Pick your mode & lives:</strong> Choose Standard or Popular — and how many lives you want to start with.</li>
                <li><strong>Listen carefully:</strong> A short clip will play each round.</li>
                <li><strong>Place the song:</strong> Drop it where you think it belongs on the timeline.</li>
                <li><strong>Right or wrong:</strong> Correct guesses keep you going; wrong ones cost a life.</li>
                <li><strong>Game end:</strong> When you run out of lives, your run ends — try again to beat your <strong>longest streak</strong> and <strong>highest score</strong>!</li>
              </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        # Game mode
        st.markdown('<div class="panel">Select Game-mode</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)

        # two centered columns, no gap on right
        spacer, g1, g2, spacer2 = st.columns([0.5, 1, 1, 0.5])

        with g1:
            if st.button("🎵  Standard", use_container_width=True, key="s_std"):
                st.session_state.single["mode"] = "Standard"

        with g2:
            if st.button("⭐  Popular", use_container_width=True, key="s_pop"):
                st.session_state.single["mode"] = "Popular"

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
                init_single_game_state()
                go("single_game")

    st.write("")
    if st.button("⬅ Back to Home", key="back_single_home"):
        go("home")


def init_single_game_state():
    """Set up singleplayer game state."""
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

    random.seed()
    starter = random.choice(pool)
    timeline = [starter]
    used_ids = {starter.track_id}
    used_years = {starter.year}
    challenge = choose_next_song(pool, used_ids, used_years)

    st.session_state.single_game = {
        "pool": pool,
        "timeline": timeline,
        "current": challenge,
        "lives_max": single_cfg.get("lives", 3),
        "lives": single_cfg.get("lives", 3),
        "score": 0,
        "streak": 0,
        "best_streak": 0,
        "mistakes": 0,
        "used_ids": used_ids,
        "used_years": used_years,
        "status": "playing",  # playing | game_over | deck_clear
        "message": "",
    }


def process_single_guess(insert_idx: int):
    """Apply backend logic for a single guess in singleplayer."""
    game = st.session_state.single_game
    if game["current"] is None or game["status"] != "playing":
        return

    timeline: List[Song] = game["timeline"]
    cand: Song = game["current"]

    correct = is_correct_insertion(timeline, cand, insert_idx)
    if correct:
        game["score"] += 1
        game["streak"] += 1
        game["best_streak"] = max(game["best_streak"], game["streak"])
        game["message"] = f"✅ Correct! “{cand.track_name}” was released in {cand.year}."
    else:
        game["lives"] -= 1
        game["mistakes"] += 1
        game["streak"] = 0
        game["message"] = f"❌ Wrong! “{cand.track_name}” was released in {cand.year}."

    # add song to timeline while < 12 songs
    if len(timeline) < 12:
        game["timeline"] = sorted(timeline + [cand], key=lambda s: s.year)

    # consume card
    game["used_ids"].add(cand.track_id)
    game["used_years"].add(cand.year)

    # game end?
    if game["lives"] <= 0:
        game["status"] = "game_over"
        game["current"] = None
        go("single_results")
        return

    next_song = choose_next_song(game["pool"], game["used_ids"], game["used_years"])
    if next_song is None:
        game["status"] = "deck_clear"
        game["current"] = None
        go("single_results")
        return

    game["current"] = next_song


# -------------------------------------------------
# Singleplayer game page
# -------------------------------------------------
def page_single_game():
    if "single_game" not in st.session_state:
        init_single_game_state()

    game = st.session_state.single_game
    current: Optional[Song] = game["current"]
    timeline: List[Song] = game["timeline"]

    # Scoreboard
    sb_col, _ = st.columns([1.5, 3])
    with sb_col:
        lives_str = hearts(game["lives"], game["lives_max"])
        st.markdown(
            f"""
            <div class="panel" style="text-align:left;">
              <div style="font-size:1.4rem; line-height:1.2;">Scoreboard</div>
              <div style="margin-top:.5rem;">Player — {lives_str}</div>
              <div>Score — <b>{game['score']}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Current challenge (center)
    center = st.columns([1, 2, 1])[1]
    with center:
        if current is not None:
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
        else:
            st.markdown(
                """
                <div class="panel" style="margin-top:1rem;">
                  No more hearts left
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Feedback
    if game["message"]:
        st.info(game["message"])  # CSS will force white color

    st.write("")

    # === Interactive timeline with slot buttons between covers ===
    if timeline:
        tl_sorted = sorted(timeline, key=lambda s: s.year)
        allowed_positions = compute_allowed_positions(tl_sorted)

        # columns: slot0, cover0, slot1, cover1, ..., coverN-1, slotN
        cols = st.columns(len(tl_sorted) * 2 + 1)

        clicked_pos: Optional[int] = None
        for p in range(len(tl_sorted) * 2 + 1):
            with cols[p]:
                if p % 2 == 0:
                    slot_index = p // 2
                    if slot_index in allowed_positions and current is not None and game["status"] == "playing":
                        with st.container():
                            st.markdown('<div class="slot-btn">', unsafe_allow_html=True)
                            if st.button(" ", key=f"slot_single_{slot_index}"):
                                clicked_pos = slot_index
                            st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.write(" ")
                else:
                    song = tl_sorted[p // 2]
                    if song.track_cover:
                        st.image(song.track_cover, use_container_width=True)
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
                              font-size:1.8rem;
                              font-weight:900;
                            ">
                              🎵
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<div style='text-align:center;font-weight:700;margin-top:.5rem;'>{song.year}</div>",
                        unsafe_allow_html=True,
                    )

        # label row
        label_cols = st.columns(len(tl_sorted) * 2 + 1)
        for p in range(len(tl_sorted) * 2 + 1):
            with label_cols[p]:
                if p % 2 == 0:
                    slot_index = p // 2
                    if slot_index not in allowed_positions:
                        st.write(" ")
                        continue

                    if slot_index == 0:
                        top = "Before"
                        bottom = f"{tl_sorted[0].year}"
                    elif slot_index == len(tl_sorted):
                        top = "After"
                        bottom = f"{tl_sorted[-1].year}"
                    else:
                        top = "Between"
                        bottom = f"{tl_sorted[slot_index - 1].year}–{tl_sorted[slot_index].year}"
                    st.markdown(
                        f"<div class='slot-label'>{top}<br/>{bottom}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.write(" ")

        if clicked_pos is not None:
            process_single_guess(clicked_pos)
            st.rerun()

    st.write("")
    col_back, col_new = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Back to setup", key="back_single_setup"):
            go("single_setup")
            st.rerun()
    with col_new:
        if st.button("🔁 New game", key="new_single_game"):
            init_single_game_state()
            st.rerun()


# -------------------------------------------------
# Singleplayer results page
# -------------------------------------------------
def page_single_results():
    if "single_game" not in st.session_state:
        go("single_setup")
        st.rerun()

    game = st.session_state.single_game
    header_logo()

    st.markdown('<div class="panel">Results</div>', unsafe_allow_html=True)
    st.write("")

    st.markdown(
        f"<div style='text-align:center;margin-top:1rem;font-size:1.2rem;'>"
        f"Your final score is <b>{game['score']}</b> 🎉"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='text-align:center;margin-top:1.5rem;'>"
        "Thank you for playing <b>HitStory</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    # Table-style layout
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.markdown("<div class='panel'>Player</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:.75rem; text-align:center;'>You</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='panel'>Score</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='margin-top:.75rem; text-align:center;'>{game['score']}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown("<div class='panel'>Longest streak</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='margin-top:.75rem; text-align:center;'>{game['best_streak']}</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.write("")
    if st.button("⬅ Back to main menu"):
        go("home")
        st.rerun()


# -------------------------------------------------
# Multiplayer setup & state
# -------------------------------------------------
def page_multi_setup():
    if "multi" not in st.session_state:
        st.session_state.multi = {"players": 2, "names": [], "mode": "Standard", "lives": 3}

    st.markdown('<div class="panel">👥 Multiplayer!</div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1.3], gap="large")

    with left:
        st.markdown('<div class="panel soft">', unsafe_allow_html=True)
        st.markdown("### How to play — Multiplayer", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="how">
              <p>Grab your friends — it's time to battle for music-timeline glory!</p>
              <ol>
                <li><strong>Players & names:</strong> Choose 2–5 players and enter everyone’s name.</li>
                <li><strong>Pick a mode & lives:</strong> Standard, Popular, or Party — plus how many lives everyone starts with.</li>
                <li><strong>Take turns:</strong> On your turn, listen to the clip and place the song where you think it belongs on the timeline.</li>
                <li><strong>Right or wrong:</strong> Correct = keep your streak. Wrong = lose a life and your streak resets.</li>
                <li><strong>Elimination:</strong> Hit zero lives and you're out.</li>
                <li><strong>Game end:</strong> The game continues until the last player standing loses all of their lives.</li>
              </ol>

              <hr/>

              <h4>Party Mode Instructions</h4>
              <ul>
                <li><strong>Streak reward:</strong> Get 3 correct in a row and a <em>random alive player</em> must take a sip.</li>
                <li><strong>Wrong guesses:</strong> A normal miss = take a sip. If you're off by <strong>3+ songs</strong> on the timeline, you must <em>chug</em>.</li>
                <li><strong>Party messages:</strong> Special messages appear when a sip or chug event is triggered (e.g. “🎉 Alice hit a streak of 3! Bob takes a sip 🍻”).</li>
              </ul>
            </div>
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
                names.append(st.text_input(f"Player {i + 1}", value=default, key=f"m_name_{i}"))
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
            f"""<div class="hint">
            Selected: <b>{st.session_state.multi['mode']}</b> •
            <b>{st.session_state.multi['lives']}</b> lives •
            Players: <b>{st.session_state.multi['players']}</b>
            </div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        mid = st.columns([1, 1, 1])[1]
        with mid:
            if st.button("Continue ➜", use_container_width=True, type="primary", key="m_next"):
                init_multi_game_state()
                go("multi_game")

    st.write("")
    if st.button("⬅ Back to Home", key="back_multi_home"):
        go("home")


def init_multi_game_state():
    """Set up multiplayer game state."""
    if "songs_all" not in st.session_state:
        try:
            st.session_state.songs_all = load_songs(DEFAULT_DATA_PATH)
        except Exception as e:
            st.error(f"Error loading songs: {e}")
            st.stop()

    all_songs = st.session_state.songs_all
    multi_cfg = st.session_state.get("multi", {"players": 2, "names": [], "mode": "Standard", "lives": 3})
    pool = build_pool(all_songs, multi_cfg.get("mode", "Standard"))
    if not pool:
        st.error("No songs available in the selected pool.")
        st.stop()

    # resolve player names
    n_players = multi_cfg.get("players", 2)
    raw_names = multi_cfg.get("names", [])
    names: List[str] = []
    for i in range(n_players):
        name = raw_names[i].strip() if i < len(raw_names) and raw_names[i] else ""
        if not name:
            name = f"Player {i + 1}"
        names.append(name)

    random.seed()
    starter = random.choice(pool)
    timeline = [starter]
    used_ids = {starter.track_id}
    used_years = {starter.year}
    challenge = choose_next_song(pool, used_ids, used_years)

    P = len(names)
    lives_max = multi_cfg.get("lives", 3)

    st.session_state.multi_game = {
        "pool": pool,
        "timeline": timeline,
        "current": challenge,
        "names": names,
        "mode": multi_cfg.get("mode", "Standard"),
        "lives_max": lives_max,
        "lives": [lives_max for _ in range(P)],
        "scores": [0 for _ in range(P)],
        "streaks": [0 for _ in range(P)],
        "best_streaks": [0 for _ in range(P)],
        "mistakes": [0 for _ in range(P)],
        "sips": [0 for _ in range(P)],
        "chugs": [0 for _ in range(P)],
        "current_idx": 0,
        "used_ids": used_ids,
        "used_years": used_years,
        "status": "playing",  # playing | game_over | deck_clear
        "message": "",
        "party_message": "",
    }


def process_multi_guess(insert_idx: int):
    """Apply backend logic for a single guess in multiplayer."""
    game = st.session_state.multi_game
    if game["current"] is None or game["status"] != "playing":
        return

    names = game["names"]
    mode = game["mode"]
    timeline: List[Song] = game["timeline"]
    cand: Song = game["current"]
    i = game["current_idx"]

    tl_sorted = sorted(timeline, key=lambda s: s.year)
    true_idx = sum(1 for s in tl_sorted if s.year < cand.year)
    offset_songs = abs(insert_idx - true_idx)

    game["party_message"] = ""

    if is_correct_insertion(timeline, cand, insert_idx):
        game["scores"][i] += 1
        game["streaks"][i] += 1
        game["best_streaks"][i] = max(game["best_streaks"][i], game["streaks"][i])
        game["message"] = (
            f"✅ Correct, {names[i]}! “{cand.track_name}” was released in {cand.year}. "
            f"Streak: {game['streaks'][i]}"
        )

        # add to timeline only while < 12 songs
        if len(timeline) < 12:
            game["timeline"] = sorted(timeline + [cand], key=lambda s: s.year)

        # Party: streak of 3 → random other alive player sips
        if mode == "Party" and game["streaks"][i] == 3:
            alive_others = [j for j, v in enumerate(game["lives"]) if v > 0 and j != i]
            if alive_others:
                target = random.choice(alive_others)
                game["sips"][target] += 1
                game["party_message"] = (
                    f"🎉 {names[i]} reached a streak of 3! "
                    f"{names[target]} takes a sip 🍻"
                )
            game["streaks"][i] = 0
    else:
        game["streaks"][i] = 0
        game["lives"][i] -= 1
        game["mistakes"][i] += 1
        game["message"] = (
            f"❌ Wrong, {names[i]}! “{cand.track_name}” was released in {cand.year}."
        )

        if mode == "Party":
            if offset_songs >= 3:
                game["chugs"][i] += 1
                game["party_message"] = "😵 Off by 3+ songs — chug your drink 🍺"
            else:
                game["sips"][i] += 1
                game["party_message"] = "👉 Take a sip 🍻"

    # consume card
    game["used_ids"].add(cand.track_id)
    game["used_years"].add(cand.year)

    if game["lives"][i] <= 0:
        game["message"] += f"  🪦 {names[i]} has been eliminated!"

    nxt = next_alive_from(game["current_idx"], game["lives"])
    if nxt is None:
        game["status"] = "game_over"
        game["current"] = None
        go("multi_results")
        return

    next_song = choose_next_song(game["pool"], game["used_ids"], game["used_years"])
    if next_song is None:
        game["status"] = "deck_clear"
        game["current"] = None
        go("multi_results")
        return

    game["current_idx"] = nxt
    game["current"] = next_song


# -------------------------------------------------
# Multiplayer game page
# -------------------------------------------------
def page_multi_game():
    if "multi_game" not in st.session_state:
        init_multi_game_state()

    game = st.session_state.multi_game
    current: Optional[Song] = game["current"]
    timeline: List[Song] = game["timeline"]
    names: List[str] = game["names"]
    mode: str = game["mode"]
    i_turn: int = game["current_idx"]

    # Scoreboard panel with all players
    sb_col, _ = st.columns([2, 3])
    with sb_col:
        rows = []
        for idx, name in enumerate(names):
            indicator = "▶ " if idx == i_turn and game["status"] == "playing" and game["lives"][idx] > 0 else ""
            lives_str = hearts(game["lives"][idx], game["lives_max"])
            extra = " 💀" if game["lives"][idx] <= 0 else ""
            rows.append(
                f"<div style='margin-bottom:.25rem;'>{indicator}<b>{name}</b> — "
                f"{lives_str} • Score: <b>{game['scores'][idx]}</b>{extra}</div>"
            )
        party_extra = ""
        if mode == "Party":
            party_extra = "<hr style='border-color:#fff3;'>" + "<br>".join(
                f"{names[idx]} — Sips: {game['sips'][idx]} • Chugs: {game['chugs'][idx]}"
                for idx in range(len(names))
            )

        sb_html = (
                "<div class='panel' style='text-align:left;'>"
                "<div style='font-size:1.4rem; line-height:1.2;'>Scoreboard</div>"
                "<div style='margin-top:.5rem;'>" + "<br>".join(rows) + "</div>"
        )
        if party_extra:
            sb_html += f"<div style='margin-top:.5rem;font-size:.85rem;'>{party_extra}</div>"
        sb_html += "</div>"
        st.markdown(sb_html, unsafe_allow_html=True)

    st.write("")

    if game["status"] == "playing":
        st.markdown(
            f"<div style='font-weight:700;margin-bottom:.5rem;'>Turn: {names[i_turn]}</div>",
            unsafe_allow_html=True,
        )

    # Current challenge (center)
    center = st.columns([1, 2, 1])[1]
    with center:
        if current is not None:
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
        else:
            st.markdown(
                """
                <div class="panel" style="margin-top:1rem;">
                  No more songs in the deck.
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Feedback + party message
    if game["message"]:
        st.info(game["message"])  # CSS now forces white

    if game.get("party_message"):
        st.markdown(
            f"<div class='party-msg'>{game['party_message']}</div>",
            unsafe_allow_html=True
        )

    st.write("")

    # timeline
    if timeline:
        tl_sorted = sorted(timeline, key=lambda s: s.year)
        allowed_positions = compute_allowed_positions(tl_sorted)

        cols = st.columns(len(tl_sorted) * 2 + 1)
        clicked_pos: Optional[int] = None

        for p in range(len(tl_sorted) * 2 + 1):
            with cols[p]:
                if p % 2 == 0:
                    slot_index = p // 2
                    if (
                            slot_index in allowed_positions
                            and current is not None
                            and game["status"] == "playing"
                            and game["lives"][i_turn] > 0
                    ):
                        with st.container():
                            st.markdown('<div class="slot-btn">', unsafe_allow_html=True)
                            if st.button(" ", key=f"slot_multi_{slot_index}"):
                                clicked_pos = slot_index
                            st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.write(" ")
                else:
                    song = tl_sorted[p // 2]
                    if song.track_cover:
                        st.image(song.track_cover, use_container_width=True)
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
                              font-size:1.8rem;
                              font-weight:900;
                            ">
                              🎵
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<div style='text-align:center;font-weight:700;margin-top:.5rem;'>{song.year}</div>",
                        unsafe_allow_html=True,
                    )

        label_cols = st.columns(len(tl_sorted) * 2 + 1)
        for p in range(len(tl_sorted) * 2 + 1):
            with label_cols[p]:
                if p % 2 == 0:
                    slot_index = p // 2
                    if slot_index not in allowed_positions:
                        st.write(" ")
                        continue

                    if slot_index == 0:
                        top = "Before"
                        bottom = f"{tl_sorted[0].year}"
                    elif slot_index == len(tl_sorted):
                        top = "After"
                        bottom = f"{tl_sorted[-1].year}"
                    else:
                        top = "Between"
                        bottom = f"{tl_sorted[slot_index - 1].year}–{tl_sorted[slot_index].year}"
                    st.markdown(
                        f"<div class='slot-label'>{top}<br/>{bottom}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.write(" ")

        if clicked_pos is not None:
            process_multi_guess(clicked_pos)
            st.rerun()

    st.write("")
    col_back, col_new = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Back to setup", key="back_multi_setup"):
            go("multi_setup")
            st.rerun()
    with col_new:
        if st.button("🔁 New multiplayer game", key="new_multi_game"):
            init_multi_game_state()
            st.rerun()


# -------------------------------------------------
# Multiplayer results page
# -------------------------------------------------
def page_multi_results():
    if "multi_game" not in st.session_state:
        go("multi_setup")
        st.rerun()

    game = st.session_state.multi_game
    names = game["names"]
    scores = game["scores"]
    best_streaks = game["best_streaks"]
    mistakes = game["mistakes"]

    header_logo()
    st.markdown('<div class="panel">Results</div>', unsafe_allow_html=True)
    st.write("")

    max_score = max(scores) if scores else 0
    winners = [names[i] for i, sc in enumerate(scores) if sc == max_score]
    if winners:
        if len(winners) == 1:
            msg = f"{winners[0]} is the winner 🏆"
        else:
            msg = "It's a tie between: " + ", ".join(winners)
        st.markdown(
            f"<div style='text-align:center;margin-top:1rem;font-size:1.2rem;'>{msg}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='text-align:center;margin-top:1.5rem;'>"
        "Thank you for playing <b>HitStory</b>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    # header row
    h1, h2, h3, h4 = st.columns([1.2, 1, 1, 1])
    with h1:
        st.markdown("<div class='panel'>Player</div>", unsafe_allow_html=True)
    with h2:
        st.markdown("<div class='panel'>Score</div>", unsafe_allow_html=True)
    with h3:
        st.markdown("<div class='panel'>Longest streak</div>", unsafe_allow_html=True)
    with h4:
        st.markdown("<div class='panel'>Mistakes</div>", unsafe_allow_html=True)

    # rows
    for idx, name in enumerate(names):
        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
        with c1:
            st.markdown(
                f"<div style='margin-top:.75rem;text-align:center;'>{name}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"<div style='margin-top:.75rem;text-align:center;'>{scores[idx]}</div>",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"<div style='margin-top:.75rem;text-align:center;'>{best_streaks[idx]}</div>",
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"<div style='margin-top:.75rem;text-align:center;'>{mistakes[idx]}</div>",
                unsafe_allow_html=True,
            )

    st.write("")
    st.write("")
    if st.button("⬅ Back to main menu", key="results_back_home"):
        go("home")
        st.rerun()


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
elif page == "single_results":
    page_single_results()
elif page == "multi_setup":
    page_multi_setup()
elif page == "multi_game":
    page_multi_game()
elif page == "multi_results":
    page_multi_results()
else:
    page_home()

