#!/usr/bin/env python3
"""
Unit tests for diffseek
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from diffseek import (
    DiffState, hash_string, derive_phrase, derive_color, WORDS,
    display_identifiers, run_diff_mode, main
)


class TestHashString:
    """Tests for hash_string function."""

    def test_hash_returns_bytes(self):
        """Hash should return bytes."""
        result = hash_string("test")
        assert isinstance(result, bytes)
        assert len(result) == 32  # SHA256 produces 32 bytes

    def test_hash_consistency(self):
        """Same input should produce same hash."""
        s = "hello world"
        assert hash_string(s) == hash_string(s)

    def test_hash_different_for_different_inputs(self):
        """Different inputs should produce different hashes."""
        assert hash_string("hello") != hash_string("world")

    def test_hash_empty_string(self):
        """Should handle empty string."""
        result = hash_string("")
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hash_unicode_characters(self):
        """Should handle Unicode/non-ASCII characters."""
        result = hash_string("Hello 世界 🌍")
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hash_special_characters(self):
        """Should handle special characters like newlines, tabs, null bytes."""
        result = hash_string("line1\nline2\ttab\x00null")
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_hash_whitespace_only(self):
        """Should handle strings with only whitespace."""
        result = hash_string("   \t\n  ")
        assert isinstance(result, bytes)
        assert len(result) == 32


class TestDerivePhrase:
    """Tests for derive_phrase function."""

    def test_default_num_words(self):
        """Should return 3 words by default."""
        h = hash_string("test")
        phrase = derive_phrase(h)
        assert len(phrase.split("-")) == 3

    def test_custom_num_words(self):
        """Should return requested number of words."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=5)
        assert len(phrase.split("-")) == 5

    def test_words_from_list(self):
        """All words should be from WORDS list."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=10)
        words = phrase.split("-")
        for word in words:
            assert word in WORDS

    def test_consistency(self):
        """Same hash should produce same phrase."""
        h = hash_string("test")
        assert derive_phrase(h) == derive_phrase(h)

    def test_zero_words(self):
        """Should handle zero words (empty phrase)."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=0)
        assert phrase == ""

    def test_single_word(self):
        """Should return single word without hyphen."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=1)
        assert "-" not in phrase
        assert phrase in WORDS

    def test_negative_num_words(self):
        """Should handle negative num_words gracefully."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=-1)
        assert phrase == ""

    def test_large_num_words(self):
        """Should handle num_words exceeding hash length."""
        h = hash_string("test")
        phrase = derive_phrase(h, num_words=100)
        words = phrase.split("-")
        assert len(words) == 100
        for word in words:
            assert word in WORDS


class TestDeriveColor:
    """Tests for derive_color function."""

    def test_returns_ansi_code(self):
        """Should return an ANSI color code."""
        h = hash_string("test")
        color = derive_color(h)
        assert color.startswith("\033[")

    def test_consistency(self):
        """Same hash should produce same color."""
        h = hash_string("test")
        assert derive_color(h) == derive_color(h)

    def test_first_color(self):
        """Should handle hash that maps to first color."""
        # Create a hash where byte at index 3 is 0
        h = bytearray(32)
        h[3] = 0
        color = derive_color(bytes(h))
        from diffseek import COLORS
        assert color == COLORS[0]

    def test_last_color(self):
        """Should handle hash that maps to last color."""
        from diffseek import COLORS
        # Create a hash where byte at index 3 maps to last color
        h = bytearray(32)
        h[3] = len(COLORS) - 1
        color = derive_color(bytes(h))
        assert color == COLORS[len(COLORS) - 1]


class TestDiffStateInit:
    """Tests for DiffState initialization."""

    def test_init_basic(self):
        """Should initialize with basic parameters."""
        state = DiffState("hello", 5, use_dfs=False)
        assert state.user_string == "hello"
        assert state.target_length == 5
        assert state.use_dfs is False
        assert len(state.char_states) == 5
        assert all(s == 0 for s in state.char_states)

    def test_init_with_dfs(self):
        """Should initialize with DFS mode."""
        state = DiffState("test", 4, use_dfs=True)
        assert state.use_dfs is True

    def test_initial_range(self):
        """Should have initial range covering full string."""
        state = DiffState("hello", 5)
        assert state.has_work()
        assert state.next_range() == (0, 5)

    def test_init_zero_target_length(self):
        """Should initialize with target_length of 0."""
        state = DiffState("hello", 0)
        assert state.target_length == 0
        assert len(state.char_states) == 0

    def test_init_target_length_one(self):
        """Should initialize with target_length of 1."""
        state = DiffState("h", 1)
        assert state.target_length == 1
        assert len(state.char_states) == 1

    def test_init_negative_target_length(self):
        """Should handle negative target_length."""
        state = DiffState("hello", -5)
        assert state.target_length == -5
        # Python allows negative list sizes, but they create empty lists
        assert len(state.char_states) == 0

    def test_init_empty_string_nonzero_target(self):
        """Should initialize with empty user_string but non-zero target."""
        state = DiffState("", 10)
        assert state.user_string == ""
        assert state.target_length == 10
        assert len(state.char_states) == 10


class TestDiffStateMarkRange:
    """Tests for DiffState.mark_range method."""

    def test_mark_matching_range(self):
        """Should mark matching range as known-good (state 1)."""
        state = DiffState("hello", 5)
        state.mark_range(0, 5, matches=True)
        assert all(s == 1 for s in state.char_states)

    def test_mark_non_matching_range(self):
        """Should mark non-matching range as possible-error (state 2)."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()  # Clear initial range
        state.mark_range(0, 5, matches=False)
        assert all(s == 2 for s in state.char_states)

    def test_mark_single_char_mismatch(self):
        """Should mark single character mismatch as definite-error (state 3)."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        state.mark_range(2, 3, matches=False)
        assert state.char_states[2] == 3

    def test_split_non_matching_range(self):
        """Should split non-matching range into two subranges."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        state.mark_range(0, 4, matches=False)
        # Should add two ranges: (0, 2) and (2, 4)
        assert len(state.ranges_to_check) == 2
        assert (0, 2) in state.ranges_to_check
        assert (2, 4) in state.ranges_to_check

    def test_mark_range_start_equals_end(self):
        """Should handle start == end (empty range)."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        state.mark_range(2, 2, matches=False)
        # Empty range gets split into two empty ranges (current behavior)
        # This documents existing behavior, though it could be optimized
        assert len(state.ranges_to_check) == 2
        assert state.ranges_to_check[0] == (2, 2)
        assert state.ranges_to_check[1] == (2, 2)

    def test_mark_range_start_greater_than_end(self):
        """Should handle start > end (invalid range)."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        initial_len = len(state.ranges_to_check)
        state.mark_range(4, 2, matches=False)
        # Should handle gracefully (may not add ranges)
        assert len(state.ranges_to_check) >= initial_len

    def test_mark_range_out_of_bounds(self):
        """Should handle out-of-bounds indices."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        # Mark range beyond target_length
        state.mark_range(10, 15, matches=True)
        # Should not crash

    def test_mark_already_marked_range(self):
        """Should handle marking already-marked ranges."""
        state = DiffState("hello", 5)
        state.mark_range(0, 5, matches=True)
        # Mark same range again
        state.mark_range(0, 5, matches=True)
        assert all(s == 1 for s in state.char_states)

    def test_mark_single_char_at_position_zero(self):
        """Should mark single character error at position 0."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        state.mark_range(0, 1, matches=False)
        assert state.char_states[0] == 3  # definite-error

    def test_mark_single_char_at_last_position(self):
        """Should mark single character error at last position."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        state.mark_range(4, 5, matches=False)
        assert state.char_states[4] == 3  # definite-error


class TestDiffStateBFS:
    """Tests for DiffState with BFS mode."""

    def test_bfs_order(self):
        """BFS should process ranges in breadth-first order."""
        state = DiffState("hello", 5, use_dfs=False)
        state.ranges_to_check.clear()
        state.ranges_to_check.append((0, 2))
        state.ranges_to_check.append((2, 4))
        state.ranges_to_check.append((4, 5))
        # BFS uses popleft, so should get (0, 2) first
        assert state.next_range() == (0, 2)
        assert state.next_range() == (2, 4)
        assert state.next_range() == (4, 5)


class TestDiffStateDFS:
    """Tests for DiffState with DFS mode."""

    def test_dfs_order(self):
        """DFS should process ranges in depth-first order."""
        state = DiffState("hello", 5, use_dfs=True)
        state.ranges_to_check.clear()
        state.ranges_to_check.append((0, 2))
        state.ranges_to_check.append((2, 4))
        state.ranges_to_check.append((4, 5))
        # DFS uses pop, so should get (4, 5) first (LIFO)
        assert state.next_range() == (4, 5)
        assert state.next_range() == (2, 4)
        assert state.next_range() == (0, 2)


class TestDiffStateHasWork:
    """Tests for DiffState.has_work method."""

    def test_has_work_initially(self):
        """Should have work initially."""
        state = DiffState("hello", 5)
        assert state.has_work()

    def test_no_work_when_empty(self):
        """Should have no work when queue is empty."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        assert not state.has_work()

    def test_next_range_on_empty_queue(self):
        """Should raise IndexError when calling next_range on empty queue."""
        state = DiffState("hello", 5)
        state.ranges_to_check.clear()
        with pytest.raises(IndexError):
            state.next_range()


class TestBinarySearchIntegration:
    """Integration tests for the binary search diff algorithm."""

    def run_search(self, reference_string, user_string, target_length=None, use_dfs=False):
        """Helper to run a complete binary search."""
        if target_length is None:
            target_length = len(reference_string)

        state = DiffState(user_string, target_length, use_dfs)
        steps = 0

        while state.has_work():
            start, end = state.next_range()
            steps += 1

            # Get substrings to compare
            ref_substr = reference_string[start:end] if end <= len(reference_string) else reference_string[start:]
            user_substr = user_string[start:end] if end <= len(user_string) else user_string[start:]

            # Compare hashes
            matches = hash_string(ref_substr) == hash_string(user_substr)
            state.mark_range(start, end, matches)

        # Extract found errors
        errors_found = [i for i in range(min(len(user_string), target_length))
                        if state.char_states[i] == 3]

        # Extract actual errors
        actual_errors = [i for i in range(min(len(reference_string), len(user_string), target_length))
                         if reference_string[i] != user_string[i]]

        return steps, errors_found, actual_errors

    def test_single_error_bfs(self):
        """Should find single character error using BFS."""
        _, errors_found, actual_errors = self.run_search("hello world", "hello warld")
        assert errors_found == actual_errors
        assert errors_found == [7]

    def test_single_error_dfs(self):
        """Should find single character error using DFS."""
        _, errors_found, actual_errors = self.run_search("hello world", "hello warld", use_dfs=True)
        assert errors_found == actual_errors
        assert errors_found == [7]

    def test_multiple_errors_bfs(self):
        """Should find multiple character errors using BFS."""
        _, errors_found, actual_errors = self.run_search("abcdefghijklmnop", "abXdefXhijXlmnop")
        assert errors_found == actual_errors
        assert errors_found == [2, 6, 10]

    def test_multiple_errors_dfs(self):
        """Should find multiple character errors using DFS."""
        _, errors_found, actual_errors = self.run_search("abcdefghijklmnop", "abXdefXhijXlmnop", use_dfs=True)
        assert errors_found == actual_errors
        assert errors_found == [2, 6, 10]

    def test_identical_strings(self):
        """Should find no errors with identical strings."""
        _, errors_found, actual_errors = self.run_search("perfectly matching string", "perfectly matching string")
        assert errors_found == actual_errors
        assert errors_found == []

    def test_length_mismatch(self):
        """Should handle strings with different lengths."""
        _, errors_found, actual_errors = self.run_search("hello world", "hello wor", target_length=11)
        assert errors_found == actual_errors
        # The algorithm only finds differences where both strings have characters
        # Missing characters are not marked as definite errors
        assert len(errors_found) == len(actual_errors)

    def test_long_string_with_errors(self):
        """Should handle longer strings with scattered errors."""
        ref = "https://example.com/auth?token=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        usr = "https://example.com/auth?token=abc123def456ghi789jkl012mno345pqr67Xstu901vwx234yZ"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors

    def test_dfs_same_or_fewer_steps(self):
        """Should verify DFS and BFS find the same errors."""
        ref = "abcdefghijklmnop"
        usr = "Xbcdefghijklmnop"  # Error at position 0

        steps_bfs, _, _ = self.run_search(ref, usr, use_dfs=False)
        steps_dfs, _, _ = self.run_search(ref, usr, use_dfs=True)

        # For the same search, both approaches should find all errors
        # DFS and BFS may take different numbers of steps depending on error positions
        assert steps_dfs <= steps_bfs
        # Both should find the same errors correctly
        _, errors_bfs, _ = self.run_search(ref, usr, use_dfs=False)
        _, errors_dfs, _ = self.run_search(ref, usr, use_dfs=True)
        assert errors_bfs == errors_dfs

    def test_all_characters_different(self):
        """Should find all errors when all characters differ."""
        ref = "aaaaaaaa"
        usr = "bbbbbbbb"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert len(errors_found) == 8

    def test_first_character_only_differs(self):
        """Should find error when only first character differs."""
        ref = "hello"
        usr = "Xello"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == [0]

    def test_last_character_only_differs(self):
        """Should find error when only last character differs."""
        ref = "hello"
        usr = "hellX"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == [4]

    def test_consecutive_errors(self):
        """Should find consecutive/adjacent errors."""
        ref = "abcdefgh"
        usr = "abXXXfgh"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == [2, 3, 4]

    def test_empty_vs_non_empty(self):
        """Should handle empty string vs non-empty string."""
        ref = ""
        usr = "hello"
        _, errors_found, _ = self.run_search(ref, usr, target_length=5)
        # Empty reference means all positions where user has chars are errors
        # But the algorithm only marks definite errors where comparison happens
        # This is a boundary case

    def test_non_empty_vs_empty(self):
        """Should handle non-empty string vs empty string."""
        ref = "hello"
        usr = ""
        _, errors_found, _ = self.run_search(ref, usr, target_length=5)
        # User string is empty, so no characters to mark as errors
        assert errors_found == []

    def test_both_empty(self):
        """Should handle both strings empty."""
        ref = ""
        usr = ""
        _, errors_found, actual_errors = self.run_search(ref, usr, target_length=0)
        assert errors_found == actual_errors
        assert errors_found == []

    def test_length_one_matching(self):
        """Should handle length-1 strings that match."""
        ref = "a"
        usr = "a"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == []

    def test_length_one_different(self):
        """Should handle length-1 strings that differ."""
        ref = "a"
        usr = "b"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == [0]

    def test_length_two_different(self):
        """Should handle length-2 strings with errors."""
        ref = "ab"
        usr = "Xb"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors
        assert errors_found == [0]

    def test_unicode_characters(self):
        """Should handle Unicode characters in strings."""
        ref = "Hello 世界"
        usr = "Hello 世X"
        _, errors_found, actual_errors = self.run_search(ref, usr)
        assert errors_found == actual_errors


class TestDisplayIdentifiers:
    """Tests for display_identifiers function."""

    def test_display_with_label(self, capsys):
        """Should display hash identifiers with label."""
        display_identifiers("test string", label="Test")
        captured = capsys.readouterr()
        assert "Test:" in captured.out
        assert "█████" in captured.out
        # Check that it contains a phrase (3 words by default)
        lines = captured.out.strip().split('\n')
        assert len(lines) == 1
        # Extract the phrase part (after the color block)
        assert "-" in captured.out  # Phrases are hyphen-separated

    def test_display_without_label(self, capsys):
        """Should display hash identifiers without label."""
        display_identifiers("test string")
        captured = capsys.readouterr()
        assert "█████" in captured.out
        # Should not have a label prefix with colon followed by space at the start
        # Check that output doesn't start with a label format like "Label: "
        first_line = captured.out.strip().split('\n')[0]
        # If there's a colon, it shouldn't be followed by the color block (indicating a label)
        assert not first_line.split("█████")[0].strip().endswith(":")

    def test_display_custom_num_words(self, capsys):
        """Should display requested number of words."""
        display_identifiers("test", num_words=5)
        captured = capsys.readouterr()
        # Extract the phrase (after the ANSI codes and color block)
        # Count hyphens - should be num_words - 1
        phrase_part = captured.out.split("█████")[-1].strip()
        word_count = len(phrase_part.split("-"))
        assert word_count == 5

    def test_display_consistency(self, capsys):
        """Same string should produce same display."""
        display_identifiers("consistent")
        output1 = capsys.readouterr().out
        display_identifiers("consistent")
        output2 = capsys.readouterr().out
        assert output1 == output2

    def test_display_empty_string(self, capsys):
        """Should handle empty string input."""
        display_identifiers("")
        captured = capsys.readouterr()
        assert "█████" in captured.out

    def test_display_zero_words(self, capsys):
        """Should handle zero words."""
        display_identifiers("test", num_words=0)
        captured = capsys.readouterr()
        assert "█████" in captured.out
        # No phrase should be displayed
        lines = captured.out.strip().split('\n')
        assert len(lines) == 1

    def test_display_unicode(self, capsys):
        """Should handle Unicode characters."""
        display_identifiers("Hello 世界 🌍", label="Unicode")
        captured = capsys.readouterr()
        assert "Unicode:" in captured.out
        assert "█████" in captured.out


class TestDiffStateDisplay:
    """Tests for DiffState.display_string method."""

    def test_display_empty_string(self, capsys):
        """Should handle empty string."""
        state = DiffState("", 0)
        state.display_string()
        captured = capsys.readouterr()
        assert "(empty string)" in captured.out

    def test_display_unknown_state(self, capsys):
        """Should display unknown characters without coloring."""
        state = DiffState("hello", 5)
        state.display_string()
        captured = capsys.readouterr()
        # Should contain the string (though may have ANSI codes)
        assert "hello" in captured.out or "h" in captured.out

    def test_display_known_good(self, capsys):
        """Should display known-good characters."""
        state = DiffState("hello", 5)
        state.char_states = [1, 1, 1, 1, 1]  # All known-good
        state.display_string()
        captured = capsys.readouterr()
        # Should contain ANSI codes for white color
        assert "\033[" in captured.out
        assert "\033[0m" in captured.out  # Reset code

    def test_display_possible_error(self, capsys):
        """Should display possible-error characters in orange."""
        state = DiffState("hello", 5)
        state.char_states = [2, 2, 2, 2, 2]  # All possible-error
        state.display_string()
        captured = capsys.readouterr()
        # Should contain ANSI codes for orange color
        assert "\033[" in captured.out

    def test_display_definite_error(self, capsys):
        """Should display definite-error characters in red."""
        state = DiffState("hello", 5)
        state.char_states = [1, 1, 3, 1, 1]  # Middle char is error
        state.display_string()
        captured = capsys.readouterr()
        # Should contain ANSI codes
        assert "\033[" in captured.out

    def test_display_mixed_states(self, capsys):
        """Should display mixed character states correctly."""
        state = DiffState("hello", 5)
        state.char_states = [1, 0, 2, 3, 1]  # Mix of all states
        state.display_string()
        captured = capsys.readouterr()
        # Should have output with ANSI codes
        assert "\033[" in captured.out

    def test_display_string_too_short(self, capsys):
        """Should indicate when string is shorter than target."""
        state = DiffState("hi", 5)
        state.display_string()
        captured = capsys.readouterr()
        assert "[3 characters missing]" in captured.out

    def test_display_truncates_to_target_length(self, capsys):
        """Should only display up to target length."""
        state = DiffState("hello world", 5)
        state.display_string()
        captured = capsys.readouterr()
        # Should not show " world" part - the output should be limited to first 5 characters
        # Remove ANSI codes to check the actual string content
        import re
        ansi_escape = re.compile(r'\033\[[0-9;]*m')
        clean_output = ansi_escape.sub('', captured.out).strip()
        # The clean output should only contain "hello", not "world"
        assert "world" not in clean_output

    def test_display_unicode_characters(self, capsys):
        """Should display Unicode characters correctly."""
        state = DiffState("世界🌍", 3)
        state.display_string()
        captured = capsys.readouterr()
        assert "世" in captured.out or len(captured.out) > 0

    def test_display_control_characters(self, capsys):
        """Should display control characters."""
        state = DiffState("hello\nworld\ttab", 15)
        state.display_string()
        captured = capsys.readouterr()
        # Should display without crashing
        assert len(captured.out) > 0


class TestRunDiffMode:
    """Tests for run_diff_mode function."""

    def test_quit_immediately(self, capsys):
        """Should handle quit command."""
        user_inputs = ["5", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out
        assert "Exiting diff mode" in captured.out

    def test_match_response(self, capsys):
        """Should handle matching range."""
        user_inputs = ["5", "y", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out

    def test_no_match_response(self, capsys):
        """Should handle non-matching range and split."""
        user_inputs = ["5", "y", "n", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out
        assert "Current string state:" in captured.out

    def test_longer_phrase(self, capsys):
        """Should handle request for longer phrase."""
        user_inputs = ["5", "y", "l", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        # The 'l' command should display a longer phrase (more words)
        # Split output into lines and find lines with phrases (contain hyphens)
        lines = captured.out.split('\n')
        phrase_lines = [line for line in lines if '-' in line and 'Range' in line]
        # Should have at least one phrase with more than 3 words (default is 3)
        # A longer phrase will have more hyphens
        has_longer_phrase = any(line.count('-') > 2 for line in phrase_lines)
        assert has_longer_phrase, "Should display a phrase with more than 3 words"

    def test_restart_search(self, capsys):
        """Should handle restart command."""
        user_inputs = ["5", "y", "r", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Restarting search" in captured.out

    def test_use_default_length(self, capsys):
        """Should use default length when Enter is pressed."""
        user_inputs = ["", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "String length: 5" in captured.out

    def test_invalid_length_input(self, capsys):
        """Should handle invalid length input gracefully."""
        user_inputs = ["abc", "y", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Invalid length" in captured.out

    def test_length_mismatch_uses_dfs(self, capsys):
        """Should use DFS when lengths don't match."""
        user_inputs = ["10", "q"]  # Target longer than actual
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out

    def test_search_completion(self, capsys):
        """Should handle search completion."""
        user_inputs = ["5", "y", "y", "n"]  # Complete search, don't restart
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Search Complete" in captured.out
        assert "No more ranges to check" in captured.out

    def test_restart_after_completion(self, capsys):
        """Should allow restart after completion."""
        user_inputs = ["5", "y", "y", "y", "y", "q"]  # Complete, restart, quit
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Search Complete" in captured.out

    def test_zero_target_length(self, capsys):
        """Should handle target_length of 0."""
        user_inputs = ["0", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("hello")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out

    def test_empty_user_string(self, capsys):
        """Should handle empty user string."""
        user_inputs = ["5", "q"]
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("")
        captured = capsys.readouterr()
        assert "Diff Mode" in captured.out

    def test_skip_known_good_ranges(self, capsys):
        """Should skip ranges that are already known-good."""
        user_inputs = ["3", "y", "y", "q"]  # Mark first range as good, should skip
        with patch('builtins.input', side_effect=user_inputs):
            run_diff_mode("abc")
        captured = capsys.readouterr()
        # After marking the full range [0:3) as good, there should be no more ranges to check
        # The output should only show the initial range once, then complete
        assert captured.out.count("Range [0:3)") == 1
        assert "Search Complete" in captured.out or "No more ranges to check" in captured.out


class TestMain:
    """Tests for main function."""

    def test_basic_flow(self, capsys):
        """Should handle basic user flow."""
        user_inputs = ["test string", "", "5", "y", "q"]
        with patch('sys.argv', ['diffseek']):
            with patch('builtins.input', side_effect=user_inputs):
                try:
                    main()
                except (StopIteration, IndexError):
                    # Input exhausted, that's OK
                    pass
        captured = capsys.readouterr()
        assert "diffseek" in captured.out or "Diff Mode" in captured.out or "String identifiers:" in captured.out

    def test_keyboard_interrupt_before_diff(self, capsys):
        """Should handle Ctrl-C before diff mode."""
        with patch('sys.argv', ['diffseek']):
            with patch('builtins.input', side_effect=["test string", KeyboardInterrupt()]):
                main()
        captured = capsys.readouterr()
        assert "Exiting" in captured.out

    def test_displays_identifiers(self, capsys):
        """Should display string identifiers."""
        user_inputs = ["hello", "", "5", "y", "q"]
        with patch('sys.argv', ['diffseek']):
            with patch('builtins.input', side_effect=user_inputs):
                try:
                    main()
                except (StopIteration, IndexError):
                    # Input exhausted, that's OK
                    pass
        captured = capsys.readouterr()
        assert "String identifiers:" in captured.out or "diffseek" in captured.out

    def test_empty_string_input(self, capsys):
        """Should handle empty string input."""
        user_inputs = ["", "", "0", "q"]
        with patch('sys.argv', ['diffseek']):
            with patch('builtins.input', side_effect=user_inputs):
                try:
                    main()
                except (StopIteration, IndexError):
                    pass
        captured = capsys.readouterr()
        assert "diffseek" in captured.out or "String identifiers:" in captured.out

    def test_unicode_string_input(self, capsys):
        """Should handle Unicode string input."""
        user_inputs = ["Hello 世界 🌍", "", "5", "y", "q"]
        with patch('sys.argv', ['diffseek']):
            with patch('builtins.input', side_effect=user_inputs):
                try:
                    main()
                except (StopIteration, IndexError):
                    pass
        captured = capsys.readouterr()
        assert "String identifiers:" in captured.out or "diffseek" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
