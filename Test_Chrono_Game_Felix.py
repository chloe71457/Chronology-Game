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
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
import pandas as pd

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