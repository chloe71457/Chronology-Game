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


st.set_page_config(page_title="HitStory", page_icon="🎵", layout="wide")
APP_DIR = Path(__file__).parent
LOGO = APP_DIR / "Logo_V1.png"

# Brand colors
PURPLE = "#2D0D57"
PANEL = "#4978C8"
PANEL_BORDER = "#2a4d98"
PINK = "#ff5aa3"
TEXT = "#ffffff"

# ------------------ Global CSS ------------------
st.markdown(
    f"""
    <style>
    :root {{
      --purple:{PURPLE}; --panel:{PANEL}; --panelBorder:{PANEL_BORDER}; --pink:{PINK}; --text:{TEXT};
    }}
    /* app background */
    [data-testid="stAppViewContainer"] {{
      background: var(--purple);
      color: var(--text);
    }}
    /* fill viewport & center vertically so no scroll on normal screens */
    [data-testid="stAppViewContainer"] > .main {{
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    /* hide default chrome */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display:none !important; }}

    /* logo */
    .hero {{ text-align:center; margin: 0 0 .5rem 0; }}
    .hero img {{
      max-width: 320px;            /* tweak if still too big/small */
      width: 48%;
      margin: 0 auto;
      display: block;
    }}

    /* panel blocks */
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

    /* bullets pink */
    .how li::marker {{ color: var(--pink); }}
    .how li {{ margin: .35rem 0; }}

    /* pink buttons */
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
    .stButton>button:active {{ transform: translateY(2px); box-shadow: 0 3px 0 #c23c79; }}

    .rowgap {{ margin: .4rem 0 .6rem 0; }}
    .hint {{ opacity:.9; font-weight:600; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ Simple router ------------------
def go(page: str):
    st.session_state.screen = page
    try:
        # new Streamlit version
        st.rerun()
    except AttributeError:
        # fallback for older versions
        from streamlit.runtime.scriptrunner import RerunException
        from streamlit.runtime.scriptrunner import rerun
        raise RerunException(rerun)

if "screen" not in st.session_state:
    st.session_state.screen = "home"

# store selections for next pages
if "single" not in st.session_state:
    st.session_state.single = {"mode": "Standard", "lives": 3}
if "multi" not in st.session_state:
    st.session_state.multi = {"players": 2, "names": [], "mode": "Standard", "lives": 3}

# ------------------ Common header ------------------
def header_logo():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    if LOGO.exists():
        st.image(LOGO.read_bytes(), use_column_width=False)
    else:
        st.markdown('<h1 style="font-weight:900;color:#fff;">HitStory</h1>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ HOME ------------------
def screen_home():
    header_logo()
    # centered button column
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.button("Singleplayer", use_container_width=True, on_click=lambda: go("single"))
        st.write("")
        st.button("Multiplayer", use_container_width=True, on_click=lambda: go("multi"))

# ------------------ SINGLEPLAYER SETUP ------------------
def screen_single():
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
              <li>If you lose all 3 lives, play again!</li>
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
            st.button("Continue ➜", use_container_width=True, type="primary", key="s_next",
                      on_click=lambda: go("single-next"))

    st.write("")
    st.button("⬅ Back to Home", key="back_single", on_click=lambda: go("home"))

# ------------------ MULTIPLAYER SETUP ------------------
def screen_multi():
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
              <li>If you lose all 3 lives, play again!</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        # Player count
        st.markdown('<div class="panel">Select number of players (2–5)</div>', unsafe_allow_html=True)
        st.markdown('<div class="rowgap"></div>', unsafe_allow_html=True)
        st.session_state.multi["players"] = st.slider("", min_value=2, max_value=5,
                                                      value=st.session_state.multi["players"], key="m_count")

        # Names
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

        # Mode
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

        # Lives
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
            st.button("Continue ➜", use_container_width=True, type="primary", key="m_next",
                      on_click=lambda: go("multi-next"))

    st.write("")
    st.button("⬅ Back to Home", key="back_multi", on_click=lambda: go("home"))

# ------------------ Router ------------------
page = st.session_state.screen
if page == "home":
    screen_home()
elif page == "single":
    screen_single()
elif page == "multi":
    screen_multi()
else:
    # Placeholder for next pages (actual gameplay screens)
    header_logo()
    st.subheader("Next page coming…")
    st.caption("We’ll wire gameplay here using your backend functions next.")
    st.button("⬅ Back to Home", key="back_next", on_click=lambda: go("home"))

# ---------------- Config ----------------
DEFAULT_DATA_PATH = "songs_input.xlsx"
MAX_LIVES = 3
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
    """
    Show only feasible insertion slots.
    - 'Between' slots are shown only if there's an actual gap (>1 year) between adjacent items.
    - Keeps one-line layout: Option 1 < (Y1) < Option 2 < (Y2) < ... < Option K
    - Type 'EXIT' to return to main menu.
    """
    tl = sorted(timeline, key=lambda x: x.year)

    print(f"🎶 Place this song:  \033[1m{challenge.label(False)}\033[0m\n")
    show_link_for_challenge(challenge)
    print("Choose where this song's year fits (or type 'EXIT' to go back):\n")

    # Build allowed insert positions (indices into a sorted-by-year list)
    # Always allow: before first (0) and after last (len(tl)).
    allowed_positions: List[int] = [0]
    for i in range(len(tl) - 1):
        left, right = tl[i], tl[i + 1]
        if right.year - left.year > 1:
            allowed_positions.append(i + 1)  # a real gap exists
    allowed_positions.append(len(tl))

    # Render the one-line options with years in between
    tokens: List[str] = []
    opt_num = 1
    tokens.append(f"Option {opt_num}")  # before first
    for i, s in enumerate(tl):
        tokens += ["<", f"\033[1m({s.year})\033[0m"]
        # If there's a valid gap after this year, show another option here
        if i < len(tl) - 1 and (tl[i + 1].year - s.year > 1):
            opt_num += 1
            tokens += ["<", f"Option {opt_num}"]
    # Always show the trailing option after the last year
    opt_num += 1
    tokens += ["<", f"Option {opt_num}"]

    print("  " + " ".join(tokens) + "\n")

    # Map user's choice number -> actual insert_idx from allowed_positions
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
def hearts(n: int, max_hearts: int = MAX_LIVES) -> str:
    return "❤️" * n + "♡" * (max_hearts - n)


def next_player_alive(current_idx: int, lives: List[int]) -> int:
    other = 1 - current_idx
    return other if lives[other] > 0 else current_idx


def choose_pool(all_songs: List[Song]) -> List[Song]:
    has_popular_data = any(s.popularity is not None for s in all_songs)

    print("\n🎵 Choose song pool:")
    print("  (1) Standard — all songs")
    if has_popular_data:
        print("  (2) Popular only — track_popularity ≥ 75")
    else:
        print("  (2) Popular only — [unavailable: no popularity data]")

    while True:
        sel = input("Your choice: ").strip()
        if sel == "1":
            return all_songs
        if sel == "2" and has_popular_data:
            popular = filter_popular(all_songs, 75)
            if not popular:
                print("No songs meet ≥75 popularity. Using Standard pool.\n")
                return all_songs
            print(f"\n🎧 Using Popular pool: {len(popular)} songs.\n")
            return popular
        print("Enter 1 or 2.\n")


# ---------------- Single-player ----------------
def play_single(song_pool: List[Song]) -> bool:
    random.seed()
    starter = random.choice(song_pool)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}
    lives, score = MAX_LIVES, 0

    print("\n" + "=" * 64)
    print("🎵  Chronology — Single Player")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}\n")
    print(f"Lives: {hearts(lives)}   Score: {score}\n")

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
            print("-" * 64)
            print(f"\033[92m✅ Correct!\033[0m   Year: {cand.year}")
            print("-" * 64 + "\n")
        else:
            lives -= 1
            print("-" * 64)
            print(f"\033[91m❌ Wrong!\033[0m   '{cand.track_name}' was {cand.year}")
            print(f"Remaining lives: {hearts(lives)}")
            print("-" * 64 + "\n")

        timeline = sorted(timeline + [cand], key=lambda s: s.year)
        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        if lives <= 0:
            print("\n💥 Game over.")
            print(f"Final score: {score}\n")
            return True


# ---------------- Two-player ----------------
def play_two(song_pool: List[Song], player_names: Tuple[str, str]) -> bool:
    random.seed()
    starter = random.choice(song_pool)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}

    pnames = [player_names[0], player_names[1]]
    lives = [MAX_LIVES, MAX_LIVES]
    scores = [0, 0]
    current = 0

    print("\n" + "=" * 64)
    print("🎵  Chronology — Two Players")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}\n")
    print(f"{pnames[0]}  Lives: {hearts(lives[0])}   Score: {scores[0]}")
    print(f"{pnames[1]}  Lives: {hearts(lives[1])}   Score: {scores[1]}\n")

    while True:
        cand = choose_next_song(song_pool, used_ids, used_years)
        if cand is None:
            print("\nNo more songs — you cleared the deck! 🎉")
            break

        if lives[current] <= 0:
            current = next_player_alive(current, lives)
        if lives[0] <= 0 and lives[1] <= 0:
            print("\n💥 Both players are out.")
            break

        render_timeline(timeline)
        print(f"Turn: \033[1m{pnames[current]}\033[0m   Lives: {hearts(lives[current])}   Score: {scores[current]}\n")
        idx = ask_position(timeline, cand)
        if idx is None:
            print("\n↩️ Returning to main menu...\n")
            return False

        if is_correct_insertion(timeline, cand, idx):
            scores[current] += 1
            print("-" * 64)
            print(f"\033[92m✅ Correct, {pnames[current]}!\033[0m   Year: {cand.year}")
            print("-" * 64 + "\n")
        else:
            lives[current] -= 1
            print("-" * 64)
            print(f"\033[91m❌ Wrong, {pnames[current]}!\033[0m   '{cand.track_name}' was {cand.year}")
            print(f"Remaining lives: {hearts(lives[current])}")
            print("-" * 64 + "\n")
            if lives[current] == 0:
                print(f"🪦 {pnames[current]} has been eliminated!\n")

        timeline = sorted(timeline + [cand], key=lambda s: s.year)
        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        if lives[0] <= 0 and lives[1] <= 0:
            print("\n💥 Both players are out.")
            break

        current = next_player_alive(current, lives)

    print("\nFinal scores:")
    print(f"  {pnames[0]} — Score: {scores[0]}   Lives: {hearts(lives[0])}")
    print(f"  {pnames[1]} — Score: {scores[1]}   Lives: {hearts(lives[1])}")

    if scores[0] > scores[1]:
        print(f"\n🏆 Winner: {pnames[0]}!")
    elif scores[1] > scores[0]:
        print(f"\n🏆 Winner: {pnames[1]}!")
    else:
        print("\n🤝 It’s a tie!")

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
        print("  (2) Two Players")
        print("  (Q) Quit")
        mode = input("Your choice: ").strip().lower()

        if mode == "q":
            break
        elif mode in ("1", "2"):
            pool = choose_pool(all_songs)

            if mode == "1":
                cont = play_single(pool)
                if not cont:
                    continue
            else:
                print("\nEnter both player names separated by a comma (e.g. Alice,Bob):")
                names_input = input("Names: ").strip()
                if not names_input:
                    pnames = ("Player 1", "Player 2")
                else:
                    parts = [p.strip() for p in names_input.split(",") if p.strip()]
                    if len(parts) < 2:
                        parts.append("Player 2")
                    pnames = (parts[0], parts[1])
                cont = play_two(pool, pnames)
                if not cont:
                    continue
        else:
            print("Invalid choice, try again.\n")

    print("\n👋 Thanks for playing!")
    sys.exit(0)


if __name__ == "__main__":
    main()