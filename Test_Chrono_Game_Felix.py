#!/usr/bin/env python3
"""
Chronology (Hitster-style) console game.

Modes:
  1️⃣  Single Player — normal mode
  2️⃣  Two Players   — alternating turns
Type "EXIT" at any placement prompt to return to main menu.
Option to show (clickable) links for the current challenge song only.
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


# ---------------- Data model ----------------
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
        raise SystemExit(f"Dataset missing columns: {missing}")

    df = df[REQUIRED_COLS].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["track_name", "track_artist", "year"])
    df["year"] = df["year"].astype(int)
    df = df.drop_duplicates(subset=["track_id", "year"]).reset_index(drop=True)

    songs = [
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
        raise SystemExit("No valid songs found.")
    return songs


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
    print("\nCurrent timeline:")
    for i, s in enumerate(sorted(timeline, key=lambda x: x.year), start=1):
        print(f"  {i}. {s.label(show_year=True)}")
    print()


# ---------------- Link helpers ----------------
def supports_ansi_hyperlinks() -> bool:
    """Best-effort check if terminal likely supports OSC 8 hyperlinks."""
    term = os.environ.get("TERM", "")
    if sys.platform == "win32":
        # Windows Terminal exposes WT_SESSION; VS Code uses VSCODE_IPC_HOOK.
        return "WT_SESSION" in os.environ or "WindowsTerminal" in os.environ or "VSCODE_PID" in os.environ
    return any(k in term for k in ("xterm", "screen", "tmux", "kitty"))

def hyperlink(url: str, text: str) -> str:
    """Return a clickable hyperlink if supported, else a plain 'text: url'."""
    if supports_ansi_hyperlinks():
        return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"
    return f"{text}: {url}"

def show_link_for_challenge(song: Song):
    """Show link only for the current challenge song."""
    if song.track_url:
        print(f"   🎧 {hyperlink(song.track_url, 'Listen here')}")
    else:
        print("   (No preview available)")


# ---------------- Prompt / options ----------------
def ask_position(timeline: List[Song], challenge: Song, show_links: bool) -> Optional[int]:
    """
    Inline options:
      Option 1 < (YYYY) < Option 2 < (YYYY) < ... < Option N
    Type "EXIT" to return to main menu.
    """
    tl = sorted(timeline, key=lambda x: x.year)

    print(f"Place this song:  \033[1m{challenge.label(False)}\033[0m")
    if show_links:
        show_link_for_challenge(challenge)

    print("Choose where this song's year fits (or type 'EXIT' to go back):")

    # Ensure a "<" between every token
    tokens: List[str] = ["Option 1"]
    for i, s in enumerate(tl):
        tokens += ["<", f"\033[1m({s.year})\033[0m", "<", f"Option {i+2}"]
    print("  " + " ".join(tokens))

    while True:
        choice = input(f"Your choice (1..{len(tl)+1}, or EXIT): ").strip().lower()
        if choice == "exit":
            return None
        try:
            val = int(choice)
            if 1 <= val <= len(tl) + 1:
                return val - 1
        except ValueError:
            pass
        print("Invalid input. Try again.")


# ---------------- Helpers ----------------
def hearts(n: int, max_hearts: int = MAX_LIVES) -> str:
    return "❤️" * n + "♡" * (max_hearts - n)

def next_player_alive(current_idx: int, lives: List[int]) -> int:
    other = 1 - current_idx
    return other if lives[other] > 0 else current_idx

def ask_yes_no(prompt: str, default: bool = False) -> bool:
    hint = " [Y/n]: " if default else " [y/N]: "
    while True:
        ans = input(prompt + hint).strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer y or n.")


# ---------------- Single-player ----------------
def play_single(all_songs: List[Song], show_links: bool) -> bool:
    random.seed()
    starter = random.choice(all_songs)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}
    lives, score = MAX_LIVES, 0

    print("\n" + "=" * 64)
    print("🎵  Chronology — Single Player")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}")
    print(f"Lives: {hearts(lives)}   Score: {score}")

    while True:
        cand = choose_next_song(all_songs, used_ids, used_years)
        if cand is None:
            print("\nNo more valid songs — you cleared the deck! 🎉")
            print(f"Final score: {score}\n")
            return True

        render_timeline(timeline)
        idx = ask_position(timeline, cand, show_links)
        if idx is None:
            print("\n↩️ Returning to main menu...\n")
            return False

        if is_correct_insertion(timeline, cand, idx):
            score += 1
            print(f"\033[92m✅ Correct!\033[0m Year: {cand.year}")
        else:
            lives -= 1
            print(f"\033[91m❌ Wrong.\033[0m '{cand.track_name}' was {cand.year}.  Lives: {hearts(lives)}")

        timeline = sorted(timeline + [cand], key=lambda s: s.year)
        used_ids.add(cand.track_id)
        used_years.add(cand.year)

        if lives <= 0:
            print("\n💥 Game over.")
            print(f"Final score: {score}\n")
            return True


# ---------------- Two-player ----------------
def play_two(all_songs: List[Song], player_names: Tuple[str, str], show_links: bool) -> bool:
    random.seed()
    starter = random.choice(all_songs)
    timeline = [starter]
    used_ids, used_years = {starter.track_id}, {starter.year}

    pnames = [player_names[0], player_names[1]]
    lives = [MAX_LIVES, MAX_LIVES]
    scores = [0, 0]
    current = 0

    print("\n" + "=" * 64)
    print("🎵  Chronology — Two Players")
    print("=" * 64)
    print(f"Starter: {starter.label(True)}")
    print(f"{pnames[0]}  Lives: {hearts(lives[0])}   Score: {scores[0]}")
    print(f"{pnames[1]}  Lives: {hearts(lives[1])}   Score: {scores[1]}")

    while True:
        cand = choose_next_song(all_songs, used_ids, used_years)
        if cand is None:
            print("\nNo more songs — you cleared the deck! 🎉")
            break

        if lives[current] <= 0:
            current = next_player_alive(current, lives)

        if lives[0] <= 0 and lives[1] <= 0:
            print("\n💥 Both players are out.")
            break

        render_timeline(timeline)
        print(f"Turn: \033[1m{pnames[current]}\033[0m   "
              f"Lives: {hearts(lives[current])}   Score: {scores[current]}")
        idx = ask_position(timeline, cand, show_links)
        if idx is None:
            print("\n↩️ Returning to main menu...\n")
            return False

        if is_correct_insertion(timeline, cand, idx):
            scores[current] += 1
            print(f"\033[92m✅ Correct, {pnames[current]}!\033[0m Year: {cand.year}   "
                  f"(Score now {scores[current]})")
        else:
            lives[current] -= 1
            print(f"\033[91m❌ Wrong, {pnames[current]}.\033[0m "
                  f"'{cand.track_name}' was {cand.year}.  Lives: {hearts(lives[current])}")
            if lives[current] == 0:
                print(f"🪦 {pnames[current]} has been eliminated!")

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
        songs = load_songs(args.data)
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
            show_links = ask_yes_no("Show clickable song links?", default=True)

            if mode == "1":
                cont = play_single(songs, show_links)
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

                cont = play_two(songs, pnames, show_links)
                if not cont:
                    continue
        else:
            print("Invalid choice, try again.")

    print("\n👋 Thanks for playing!")
    sys.exit(0)


if __name__ == "__main__":
    main()