"""Unit tests for launcher helper functions."""

import sys
import os

# Ensure the project root is on the path when running tests from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from launcher import parse_fzf_selection, FZF_DISPLAY_DELIM


DELIM = FZF_DISPLAY_DELIM  # " | "


class TestParseFzfSelection:
    """Tests for parse_fzf_selection."""

    def test_normal_line(self):
        """Standard three-part line returns the last field (desktop_id)."""
        line = f"VLC media player{DELIM}Video;AudioVideo{DELIM}vlc.desktop"
        assert parse_fzf_selection(line) == "vlc.desktop"

    def test_strips_whitespace(self):
        """Trailing/leading whitespace around the desktop_id is stripped."""
        line = f"App{DELIM}Cat{DELIM}  my.desktop  "
        assert parse_fzf_selection(line) == "my.desktop"

    def test_empty_categories(self):
        """Category field may be empty; desktop_id is still the last part."""
        line = f"App{DELIM}{DELIM}nocat.desktop"
        assert parse_fzf_selection(line) == "nocat.desktop"

    def test_none_on_empty_string(self):
        assert parse_fzf_selection("") is None

    def test_none_on_whitespace_only(self):
        assert parse_fzf_selection("   ") is None

    def test_none_on_none_input(self):
        assert parse_fzf_selection(None) is None  # type: ignore[arg-type]

    def test_none_when_fewer_than_three_parts(self):
        """A line without enough delimiters should return None."""
        assert parse_fzf_selection(f"App{DELIM}only-two-parts") is None

    def test_exactly_three_parts(self):
        line = f"Firefox{DELIM}Network{DELIM}firefox.desktop"
        assert parse_fzf_selection(line) == "firefox.desktop"

    def test_desktop_id_with_dots_and_hyphens(self):
        """Desktop IDs can contain dots, hyphens, underscores."""
        line = f"GIMP{DELIM}Graphics{DELIM}org.gnome.gimp-2.10.desktop"
        assert parse_fzf_selection(line) == "org.gnome.gimp-2.10.desktop"
