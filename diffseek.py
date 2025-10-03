#!/usr/bin/env python3
"""
diffseek - A tool for comparing long strings across devices via binary search
"""

__version__ = "0.1.1"

import argparse
import hashlib
import sys
from collections import deque

# Word list for generating memorable phrases
WORDS = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey", "xray",
    "yankee", "zulu", "anchor", "beacon", "castle", "dragon", "eagle", "falcon",
    "granite", "hammer", "island", "jungle", "kernel", "laser", "mountain", "nebula",
    "ocean", "palace", "quartz", "river", "summit", "tiger", "universe", "valley",
    "winter", "xenon", "yellow", "zenith", "amber", "bronze", "copper", "diamond",
    "emerald", "flame", "garnet", "honey", "ivory", "jade", "knight", "lemon"
]

# ANSI color codes
COLORS = [
    "\033[31m",  # Red
    "\033[32m",  # Green
    "\033[33m",  # Yellow
    "\033[34m",  # Blue
    "\033[35m",  # Magenta
    "\033[36m",  # Cyan
    "\033[91m",  # Bright Red
    "\033[92m",  # Bright Green
    "\033[93m",  # Bright Yellow
    "\033[94m",  # Bright Blue
    "\033[95m",  # Bright Magenta
    "\033[96m",  # Bright Cyan
]
RESET = "\033[0m"
ORANGE = "\033[38;5;208m"
WHITE = "\033[97m"
RED = "\033[91m"


def hash_string(s):
    """Hash a string and return the digest."""
    return hashlib.sha256(s.encode()).digest()


def derive_phrase(hash_digest, num_words=3):
    """Derive a memorable phrase from a hash.

    Args:
        hash_digest: The hash to derive from
        num_words: Number of words to include in the phrase (default 3)
    """
    words = [WORDS[hash_digest[i % len(hash_digest)] % len(WORDS)] for i in range(num_words)]
    return "-".join(words)


def derive_color(hash_digest):
    """Derive a color from a hash."""
    color_idx = hash_digest[3] % len(COLORS)
    return COLORS[color_idx]


def display_identifiers(s, label="", num_words=3):
    """Display hash-derived identifiers for a string."""
    h = hash_string(s)
    phrase = derive_phrase(h, num_words)
    color = derive_color(h)

    if label:
        print(f"{label}: ", end="")
    print(f"{color}█████{RESET} {phrase}")


class DiffState:
    """Tracks the state of the binary search diff process."""

    def __init__(self, user_string, target_length, use_dfs=False):
        self.user_string = user_string
        self.target_length = target_length
        self.use_dfs = use_dfs
        # Track character states: 0=unknown, 1=known-good, 2=possible-error, 3=definite-error
        self.char_states = [0] * target_length
        # Queue of ranges to check: (start, end)
        self.ranges_to_check = deque()
        self.ranges_to_check.append((0, target_length))

    def display_string(self):
        """Display the user string with color coding."""
        if not self.user_string:
            print("(empty string)")
            return

        # Extend or truncate display based on target length
        display_len = min(len(self.user_string), self.target_length)

        result = []
        for i in range(display_len):
            char = self.user_string[i]
            state = self.char_states[i]

            if state == 1:  # known-good
                result.append(f"{WHITE}{char}{RESET}")
            elif state == 2:  # possible-error
                result.append(f"{ORANGE}{char}{RESET}")
            elif state == 3:  # definite-error
                result.append(f"{RED}{char}{RESET}")
            else:  # unknown
                result.append(char)

        print("".join(result))

        # If string is too short, indicate missing characters
        if len(self.user_string) < self.target_length:
            missing = self.target_length - len(self.user_string)
            print(f"{RED}[{missing} characters missing]{RESET}")

    def mark_range(self, start, end, matches):
        """Mark a range as matching or not matching."""
        if matches:
            # Mark as known-good
            for i in range(start, end):
                if i < len(self.char_states):
                    self.char_states[i] = 1
        else:
            # Mark as possible-error
            for i in range(start, end):
                if i < len(self.char_states):
                    self.char_states[i] = 2

            # If it's a single character, mark as definite-error
            if end - start == 1:
                if start < len(self.char_states):
                    self.char_states[start] = 3
            else:
                # Split range and add to queue
                mid = (start + end) // 2
                self.ranges_to_check.append((start, mid))
                self.ranges_to_check.append((mid, end))

    def has_work(self):
        """Check if there are more ranges to check."""
        return len(self.ranges_to_check) > 0

    def next_range(self):
        """Get the next range to check."""
        if self.use_dfs:
            return self.ranges_to_check.pop()
        else:
            return self.ranges_to_check.popleft()


def run_diff_mode(user_string):
    """Run the binary search diff mode."""
    print(f"\n--- Diff Mode ---")
    print(f"String length: {len(user_string)}")

    # Ask for target length
    target_input = input("Target length (press Enter to use current length): ").strip()
    if target_input:
        try:
            target_length = int(target_input)
        except ValueError:
            print("Invalid length, using current length")
            target_length = len(user_string)
    else:
        target_length = len(user_string)

    # Determine search strategy based on length match
    if target_length == len(user_string):
        # Lengths match on this device, check if other device also matches
        other_matches = input("Does the other device also have matching target and actual lengths? (y/n): ").strip().lower()
        use_dfs = (other_matches != 'y')
    else:
        # Length mismatch on this device, use DFS
        use_dfs = True

    state = DiffState(user_string, target_length, use_dfs)

    while True:
        if not state.has_work():
            print("\n--- Search Complete ---")
            state.display_string()
            print("\nNo more ranges to check.")

            choice = input("\nRestart search? (y/n): ").strip().lower()
            if choice == 'y':
                # Re-determine strategy for restart
                if target_length == len(user_string):
                    other_matches = input("Does the other device also have matching target and actual lengths? (y/n): ").strip().lower()
                    use_dfs = (other_matches != 'y')
                else:
                    use_dfs = True
                state = DiffState(user_string, target_length, use_dfs)
                continue
            else:
                break

        start, end = state.next_range()

        # Skip ranges that are already known-good
        if all(state.char_states[i] == 1 for i in range(start, min(end, len(state.char_states)))):
            continue

        print(f"\n--- Checking characters {start} to {end-1} ---")

        # Get substring to check
        substring = user_string[start:end] if end <= len(user_string) else user_string[start:]

        # Track phrase length for this range
        phrase_words = 3
        display_identifiers(substring, f"Range [{start}:{end})", phrase_words)

        # Ask if it matches
        while True:
            response = input("Does this match? (y/n/l=longer phrase/r=restart/q=quit): ").strip().lower()
            if response in ['y', 'n', 'r', 'q']:
                break
            elif response == 'l':
                # Generate longer phrase
                phrase_words += 3
                display_identifiers(substring, f"Range [{start}:{end})", phrase_words)
            else:
                print("Please enter y, n, l, r, or q")

        if response == 'q':
            print("Exiting diff mode")
            break
        elif response == 'r':
            print("Restarting search...")
            # Re-determine strategy for restart
            if target_length == len(user_string):
                other_matches = input("Does the other device also have matching target and actual lengths? (y/n): ").strip().lower()
                use_dfs = (other_matches != 'y')
            else:
                use_dfs = True
            state = DiffState(user_string, target_length, use_dfs)
            continue

        matches = (response == 'y')
        state.mark_range(start, end, matches)

        # Display current state
        print("\nCurrent string state:")
        state.display_string()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Compare long strings across devices via binary search')
    args = parser.parse_args()

    print("=== diffseek ===")
    print("Enter your string:")

    # Get input
    user_string = input()

    # Display identifiers
    print("\nString identifiers:")
    display_identifiers(user_string, "Full string")

    # Wait for Enter to start diff mode
    print("\nPress Enter to start diff mode, or Ctrl-C to exit...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nExiting")
        return

    # Run diff mode
    run_diff_mode(user_string)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)
