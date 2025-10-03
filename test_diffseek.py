#!/usr/bin/env python3
"""
Test script for diffseek's binary search logic
"""

import sys
sys.path.insert(0, '/home/user/workspace/differ')

from diffseek import DiffState, hash_string


def simulate_search(reference_string, user_string, target_length=None, use_dfs=False):
    """Simulate a binary search diff process."""
    if target_length is None:
        target_length = len(reference_string)

    state = DiffState(user_string, target_length, use_dfs)
    steps = 0
    first_error_step = None

    mode = "DFS" if use_dfs else "BFS"
    print(f"Mode: {mode}")
    print(f"Reference: {reference_string}")
    print(f"User:      {user_string}")
    print(f"Target length: {target_length}\n")

    while state.has_work():
        start, end = state.next_range()
        steps += 1

        # Get substrings to compare
        ref_substr = reference_string[start:end] if end <= len(reference_string) else reference_string[start:]
        user_substr = user_string[start:end] if end <= len(user_string) else user_string[start:]

        # Compare hashes
        matches = hash_string(ref_substr) == hash_string(user_substr)

        print(f"Step {steps}: Range [{start}:{end}) - {'MATCH' if matches else 'DIFF'}")

        state.mark_range(start, end, matches)

        # Track when we first find a definite error
        if first_error_step is None and end - start == 1 and not matches:
            first_error_step = steps

    print(f"\nCompleted in {steps} steps")
    if first_error_step:
        print(f"First error found at step: {first_error_step}")
    print("Final state:")
    state.display_string()

    # Verify results
    errors_found = []
    for i in range(min(len(user_string), target_length)):
        if state.char_states[i] == 3:  # definite-error
            errors_found.append(i)

    # Find actual errors
    actual_errors = []
    for i in range(min(len(reference_string), len(user_string), target_length)):
        if reference_string[i] != user_string[i]:
            actual_errors.append(i)

    print(f"\nErrors found: {errors_found}")
    print(f"Actual errors: {actual_errors}")
    print(f"Correct: {errors_found == actual_errors}")

    return steps, errors_found == actual_errors, first_error_step


def test_single_error():
    """Test with a single character error."""
    print("=== Test 1: Single character error ===")
    simulate_search("hello world", "hello warld")
    print("\n")


def test_multiple_errors():
    """Test with multiple character errors."""
    print("=== Test 2: Multiple character errors ===")
    simulate_search("abcdefghijklmnop", "abXdefXhijXlmnop")
    print("\n")


def test_length_mismatch():
    """Test with different length strings."""
    print("=== Test 3: Length mismatch (too short) ===")
    simulate_search("hello world", "hello wor", target_length=11)
    print("\n")


def test_identical():
    """Test with identical strings."""
    print("=== Test 4: Identical strings ===")
    simulate_search("perfectly matching string", "perfectly matching string")
    print("\n")


def test_long_string():
    """Test with a longer string."""
    print("=== Test 5: Long string with scattered errors ===")
    ref = "https://example.com/auth?token=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
    usr = "https://example.com/auth?token=abc123def456ghi789jkl012mno345pqr67Xstu901vwx234yZ"
    simulate_search(ref, usr)
    print("\n")


def test_dfs_mode():
    """Test DFS mode finds first error faster."""
    print("=== Test 6: DFS mode (single error) ===")
    simulate_search("hello world", "hello warld", use_dfs=True)
    print("\n")


def test_dfs_multiple_errors():
    """Test DFS mode with multiple errors."""
    print("=== Test 7: DFS mode (multiple errors) ===")
    simulate_search("abcdefghijklmnop", "abXdefXhijXlmnop", use_dfs=True)
    print("\n")


def test_bfs_vs_dfs_comparison():
    """Compare BFS and DFS for finding first error."""
    print("=== Test 8: BFS vs DFS comparison ===")
    ref = "abcdefghijklmnop"
    usr = "abXdefXhijXlmnop"

    print("--- BFS Mode ---")
    steps_bfs, correct_bfs, first_error_bfs = simulate_search(ref, usr, use_dfs=False)

    print("\n--- DFS Mode ---")
    steps_dfs, correct_dfs, first_error_dfs = simulate_search(ref, usr, use_dfs=True)

    print(f"\n--- Comparison ---")
    print(f"BFS: {steps_bfs} total steps, first error at step {first_error_bfs}")
    print(f"DFS: {steps_dfs} total steps, first error at step {first_error_dfs}")
    print(f"DFS found first error {first_error_bfs - first_error_dfs} steps faster")
    print("\n")


if __name__ == "__main__":
    test_single_error()
    test_multiple_errors()
    test_length_mismatch()
    test_identical()
    test_long_string()
    test_dfs_mode()
    test_dfs_multiple_errors()
    test_bfs_vs_dfs_comparison()
