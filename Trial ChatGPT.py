#!/usr/bin/env python3
"""
Chronology (Hitster-style) console game.

- First song is random (year shown).
- Each new song is random, not repeated, and not from a year already on the timeline.
- Insert it at the correct position by year (strictly increasing).
- 3 wrong guesses = game over.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import pandas as pd

# ---------------- Config ----------------
DEFAULT_DATA_PATH = "songs_input.xlsx"   # <-- your file
MAX_LIVES = 3
REQUIRED_COLS = ["track_id", "track_name", "track_artist", "year", "track_url"]

# -------------- Data model --------------
@dataclass(frozen=True)
class Song:
    track_id: int | str
    track_name: str
    track_artist: str
    year: int
    track_url: str | None = None

    def label(self, show_year: bool = False) -> str:
        base = f"{self.track_name} — {self.track_artist}"
        return f"{base} ({self.year})" if show_year else base

# -------------- Loading utils -----------
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
        raise SystemExit(f"Dataset missing columns: {missing}. Expected: {REQUIRED_COLS}")

    df = df[REQUIRED_COLS].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["track_name", "track_artist", "year"])
    df["year"] = df["year"].astype(int)
    df = df.drop_duplicates(subset=["track_id", "year"]).reset_index(drop=True)

    songs: List[Song] = [
        Song(
            track_id=row.track_id,
            track_name=row.track_name,
            track_artist=row.track_artist,
            year=int(row.year),
            track_url=(None if pd.isna(row.track_url) else str(row.track_url)),
        )
        for row in df.itertuples(index=False)
    ]
    if not songs:
        raise SystemExit("No valid songs found after cleaning.")
    return songs

# -------------- Game mechanics ----------
def choose_next_song(pool: List[Song], used_ids: Set, used_years: Set[int]) -> Optional[Song]:
    candidates = [s for s in pool if s.track_id not in used_ids and s.year not in used_years]
    return random.choice(candidates) if candidates else None

def is_correct_insertion(timeline: List[Song], new_song: Song, insert_idx: int) -> bool:
    tl_sorted = sorted(timeline, key=lambda s: s.year)
    tentative = tl_sorted[:insert_idx] + [new_song] + tl_sorted[insert_idx:]
    years = [s.year for s in tentative]
    return years == sorted(years) and len(years) == len(set(years))

def render_timeline(timeline: List[Song]) -> None:
    print("\nCurrent timeline:")
    for i, s in enumerate(sorted(timeline, key=lambda x: x.year), start=1):
        print(f"  {i}. {s.label(show_year=True)}")
    print()

def ask_position(timeline: List[Song], challenge: Song) -> int:
    tl = sorted(timeline, key=lambda x: x.year)
    options: List[Tuple[int, str]] = []
    options.append((0, f"Position 1 (before {tl[0].label(show_year=True)})"))
    for idx in range(1, len(tl)):
        left = tl[idx - 1].label(show_year=True)
        right = tl[idx].label(show_year=True)
        options.append((idx, f"Between {left}  and  {right}"))
    options.append((len(tl), f"After {tl[-1].label(show_year=True)}"))

    print(f"Place this song:  \033[1m{challenge.label(False)}\033[0m")
    for i, (_, text) in enumerate(options, start=1):
        print(f"  [{i}] {text}")

    while True:
        try:
            choice = int(input(f"Your choice (1..{len(options)}): ").strip())
            if 1 <= choice <= len(options):
                return options[choice - 1][0]
        except (ValueError, KeyboardInterrupt):
            pass
        print("Invalid input. Try again.")

# ----------------- Game loop ------------
def play_round(all_songs: List[Song]) -> None:
    random.seed()
    starter = random.choice(all_songs)
    timeline: List[Song] = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}
    lives, score = MAX_LIVES, 0

    print("\n" + "=" * 64)
    print("🎵  Chronology — Hitster-style (Console)")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}")
    print(f"Lives: {lives}   Score: {score}")

    while True:
        cand = choose_next_song(all_songs, used_ids, used_years)
        if cand is None:
            print("\nNo more valid songs to draw — you cleared the deck! 🎉")
            print(f"Final score: {score}\n")
            return

        render_timeline(timeline)
        idx = ask_position(timeline, cand)

        if is_correct_insertion(timeline, cand, idx):
            score += 1
            print(f"\n✅ Correct! Year: {cand.year}")
        else:
            lives -= 1
            print(f"\n❌ Wrong. '{cand.track_name}' was {cand.year}.  Lives left: {lives}")

        # reveal and add in true position
        timeline = sorted(timeline + [cand], key=lambda s: s.year)
        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        if lives <= 0:
            print("\n💥 Game over.")
            print(f"Final score: {score}\n")
            return

# -------------------- Main --------------
def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Hitster-style chronology game (console).")
    parser.add_argument("data", nargs="?", default=DEFAULT_DATA_PATH,
                        help="Path to .xlsx/.csv with columns: track_id, track_name, track_artist, year, track_url")
    args = parser.parse_args(argv)
    try:
        songs = load_songs(args.data)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

    while True:
        play_round(songs)
        again = input("Play again? [y/N]: ").strip().lower()
        if again != "y":
            break
    print("Thanks for playing! 👋")

if __name__ == "__main__":
    main()
